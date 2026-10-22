"""REST API for an administrative, synthetic-only demonstration.

Never interpret outputs as clinical advice or claim HIPAA/DPDP certification.
"""
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from .agents import investigate
from .config import get_settings
from .database import Base, SessionLocal, engine, session_scope
from .fixtures import CASES
from .models import AuditEvent, Case, Task, User
from .security import current_user, hash_password, make_token, require_roles, verify_password


def bootstrap():
    cfg = get_settings()
    if len(cfg.jwt_secret) < 32 or not cfg.admin_username or len(cfg.admin_password) < 12:
        raise RuntimeError("Set JWT_SECRET (32+ chars), ADMIN_USERNAME and ADMIN_PASSWORD (12+ chars) securely")
    Base.metadata.create_all(bind=engine)  # Demo startup only; production requires migrations.
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.username == cfg.admin_username)):
            db.add(User(username=cfg.admin_username, password_hash=hash_password(cfg.admin_password),
                        role="admin", tenant_id="demo-hospital"))
        if cfg.seed_demo_data:
            for item in CASES:
                if db.scalar(select(Case).where(Case.external_ref == item["external_ref"])) is None:
                    db.add(Case(**item, tenant_id="demo-hospital", status="NEW"))
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap()
    yield


app = FastAPI(title="CareFlow Nexus", version="0.1.0", lifespan=lifespan,
              description="Administrative discharge-case workbench. Demo datasets are fully synthetic.")
app.add_middleware(CORSMiddleware, allow_origins=[s.strip() for s in get_settings().cors_origins.split(",")],
                   allow_credentials=False, allow_methods=["GET", "POST"],
                   allow_headers=["Authorization", "Content-Type"])


class LoginRequest(BaseModel):
    username: str
    password: str


class NewUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=12)
    role: Literal["analyst", "supervisor", "auditor"]


class DecisionRequest(BaseModel):
    plan_version: int = Field(ge=1)
    decision: Literal["APPROVED", "REJECTED"]


def check_case(db: Session, user: User, case_id: str) -> Case:
    item = db.scalar(select(Case).where(Case.id == case_id, Case.tenant_id == user.tenant_id))
    if item is None:
        raise HTTPException(404, "Case not found")
    return item


def log(db: Session, case: Case, username: str, action: str, detail: dict):
    db.add(AuditEvent(tenant_id=case.tenant_id, case_id=case.id, actor=username, event_type=action, detail=detail))


def task_dict(task: Task) -> dict:
    return {"id": task.id, "key": task.task_key, "title": task.title, "reason": task.reason,
            "evidence_ids": task.evidence_ids, "status": task.status, "plan_version": task.plan_version,
            "decided_by": task.decided_by}


def case_dict(case: Case, include_record: bool = False) -> dict:
    result = {"id": case.id, "reference": case.external_ref, "patient_ref": case.patient_ref,
              "service": case.service, "priority": case.priority, "status": case.status,
              "plan_version": case.plan_version, "created_at": case.created_at.isoformat()}
    if include_record:
        result.update({"record": case.record, "findings": case.findings, "evidence": case.evidence, "trace": case.trace})
    return result


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "careflow-nexus", "dataset": "synthetic-only"}


@app.post("/api/v1/auth/token")
def login(payload: LoginRequest, db: Session = Depends(session_scope)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return {"access_token": make_token(user), "token_type": "bearer", "role": user.role,
            "username": user.username, "tenant_id": user.tenant_id}


@app.post("/api/v1/users", status_code=201)
def add_user(payload: NewUserRequest, admin: User = Depends(require_roles("admin")),
             db: Session = Depends(session_scope)):
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(409, "Username already exists")
    db.add(User(username=payload.username, password_hash=hash_password(payload.password), role=payload.role,
                tenant_id=admin.tenant_id))
    db.commit()
    return {"username": payload.username, "role": payload.role}


@app.get("/api/v1/me")
def me(user: User = Depends(current_user)):
    return {"username": user.username, "role": user.role, "tenant_id": user.tenant_id}


@app.get("/api/v1/metrics")
def metrics(user: User = Depends(current_user), db: Session = Depends(session_scope)):
    cases = db.scalars(select(Case).where(Case.tenant_id == user.tenant_id)).all()
    ids = [c.id for c in cases]
    tasks = db.scalars(select(Task).where(Task.case_id.in_(ids))).all() if ids else []
    by_status = Counter(c.status for c in cases)
    return {"total_cases": len(cases), "review_required": by_status.get("REVIEW_REQUIRED", 0),
            "new_cases": by_status.get("NEW", 0), "proposed_tasks": sum(t.status == "PROPOSED" for t in tasks),
            "approved_tasks": sum(t.status == "APPROVED" for t in tasks)}


@app.get("/api/v1/cases")
def list_cases(user: User = Depends(current_user), db: Session = Depends(session_scope)):
    items = db.scalars(select(Case).where(Case.tenant_id == user.tenant_id).order_by(Case.external_ref)).all()
    return [case_dict(c) for c in items]


@app.get("/api/v1/cases/{case_id}")
def read_case(case_id: str, user: User = Depends(current_user), db: Session = Depends(session_scope)):
    case = check_case(db, user, case_id)
    data = case_dict(case, include_record=True)
    data["tasks"] = [task_dict(t) for t in db.scalars(select(Task).where(Task.case_id == case.id).order_by(Task.task_key))]
    return data


@app.post("/api/v1/cases/{case_id}/investigate")
def investigate_case(case_id: str, user: User = Depends(require_roles("admin", "analyst", "supervisor")),
                     db: Session = Depends(session_scope)):
    case = check_case(db, user, case_id)
    result = investigate(case.record)
    new_version = case.plan_version + 1
    # Remove stale unapproved plans but preserve historical decisions.
    stale = db.scalars(select(Task).where(Task.case_id == case.id, Task.status == "PROPOSED")).all()
    for task in stale:
        db.delete(task)
    existing_keys = {t.task_key for t in db.scalars(select(Task).where(Task.case_id == case.id, Task.status.in_(["APPROVED", "REJECTED"])))}
    created_drafts = 0
    for proposed in result["tasks"]:
        if proposed["key"] not in existing_keys:
            created_drafts += 1
            db.add(Task(case_id=case.id, task_key=proposed["key"], title=proposed["title"],
                        reason=proposed["reason"], evidence_ids=proposed["evidence_ids"],
                        plan_version=new_version))
    case.plan_version = new_version
    case.findings = result["findings"]
    case.evidence = result["evidence"]
    case.trace = result["trace"] + [{"agent": "SYSTEM", "action": "Validate evidence identifiers and produce read-only task drafts", "execution_mode": result["execution_mode"], "evidence_hash": result["evidence_hash"], "status": "completed"}]
    case.status = "REVIEW_REQUIRED" if created_drafts else ("REVIEW_COMPLETE" if existing_keys else "NO_FINDINGS")
    log(db, case, user.username, "INVESTIGATION_COMPLETED", {"version": new_version, "finding_codes": [f["code"] for f in result["findings"]], "execution_mode": result["execution_mode"]})
    db.commit()
    return read_case(case_id, user, db)


@app.post("/api/v1/cases/{case_id}/tasks/{task_id}/decision")
def decide_task(case_id: str, task_id: str, payload: DecisionRequest,
                user: User = Depends(require_roles("admin", "supervisor")), db: Session = Depends(session_scope)):
    case = check_case(db, user, case_id)
    task = db.scalar(select(Task).where(Task.id == task_id, Task.case_id == case.id))
    if task is None:
        raise HTTPException(404, "Task not found")
    if task.plan_version != payload.plan_version or case.plan_version != payload.plan_version:
        raise HTTPException(409, "Stale plan; refresh case before approval")
    if task.status != "PROPOSED":
        if task.status == payload.decision:
            return task_dict(task)  # Idempotent replay, no additional audit entry.
        raise HTTPException(409, "Task already decided differently")
    updated = db.execute(update(Task).where(Task.id == task_id, Task.status == "PROPOSED",
                                            Task.plan_version == payload.plan_version)
                         .values(status=payload.decision, decided_by=user.username, decided_at=datetime.now(timezone.utc)))
    if updated.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Task was changed concurrently")
    log(db, case, user.username, "TASK_DECISION", {"task_id": task_id, "decision": payload.decision,
                                                    "plan_version": payload.plan_version})
    db.commit()
    db.refresh(task)
    return task_dict(task)


@app.get("/api/v1/cases/{case_id}/audit")
def audit(case_id: str, user: User = Depends(current_user), db: Session = Depends(session_scope)):
    case = check_case(db, user, case_id)
    events = db.scalars(select(AuditEvent).where(AuditEvent.case_id == case.id,
                 AuditEvent.tenant_id == user.tenant_id).order_by(AuditEvent.created_at)).all()
    return [{"id": e.id, "actor": e.actor, "event": e.event_type, "detail": e.detail,
             "created_at": e.created_at.isoformat()} for e in events]


@app.get("/api/v1/cases/{case_id}/tasks/{task_id}/fhir")
def task_fhir_preview(case_id: str, task_id: str, user: User = Depends(current_user),
                      db: Session = Depends(session_scope)):
    """Safe local R4 preview only; does NOT write to an external FHIR server."""
    case = check_case(db, user, case_id)
    task = db.scalar(select(Task).where(Task.id == task_id, Task.case_id == case.id))
    if not task:
        raise HTTPException(404, "Task not found")
    return {"resourceType": "Task", "id": task.id, "status": "requested" if task.status == "APPROVED" else "draft",
            "intent": "order", "description": task.title, "for": {"reference": f"Patient/{case.patient_ref}"},
            "focus": {"reference": f"Encounter/{case.record['encounter']}"},
            "note": [{"text": "DEMO / SYNTHETIC ONLY. No clinical advice or external write."}]}
