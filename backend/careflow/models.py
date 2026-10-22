from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="analyst")
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, default="demo-hospital")


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    external_ref: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    patient_ref: Mapped[str] = mapped_column(String(50), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    service: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="NEW")
    priority: Mapped[str] = mapped_column(String(15), nullable=False, default="NORMAL")
    record: Mapped[dict] = mapped_column(JSON, nullable=False)
    findings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    trace: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (UniqueConstraint("case_id", "task_key", name="uq_case_task_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), nullable=False, index=True)
    task_key: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(25), nullable=False, default="PROPOSED")
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    decided_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), nullable=False)
    actor: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(70), nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now)
