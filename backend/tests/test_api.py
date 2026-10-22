import os
from pathlib import Path
import tempfile

DATA_DIR = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(DATA_DIR.name) / 'test.db'}"
os.environ["JWT_SECRET"] = "test-secret-please-change-me-0123456789ABCDEF"
os.environ["ADMIN_USERNAME"] = "testadmin"
os.environ["ADMIN_PASSWORD"] = "A-very-long-unique-test-password"
os.environ["SEED_DEMO_DATA"] = "true"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from careflow.main import app  # noqa: E402
from careflow.database import SessionLocal  # noqa: E402
from careflow.models import Case, User  # noqa: E402
from careflow.security import hash_password  # noqa: E402


def client_and_token():
    client = TestClient(app)
    client.__enter__()
    response = client.post("/api/v1/auth/token", json={"username": "testadmin", "password": "A-very-long-unique-test-password"})
    assert response.status_code == 200, response.text
    return client, {"Authorization": "Bearer " + response.json()["access_token"]}


def test_auth_and_case_lifecycle():
    client, headers = client_and_token()
    try:
        assert client.get("/api/v1/cases").status_code == 403 or client.get("/api/v1/cases").status_code == 401
        items = client.get("/api/v1/cases", headers=headers).json()
        assert len(items) == 5
        case = next(c for c in items if c["reference"] == "CASE-1001")
        review = client.post(f"/api/v1/cases/{case['id']}/investigate", headers=headers)
        assert review.status_code == 200, review.text
        data = review.json()
        assert any(f["code"] == "RECORD_CONFLICT" for f in data["findings"])
        assert len(data["tasks"]) == 2
        refs = {e["id"] for e in data["evidence"]}
        assert all(set(f["evidence_ids"]) <= refs for f in data["findings"])
        assert all(set(t["evidence_ids"]) <= refs for t in data["tasks"])
        task = data["tasks"][0]
        path = f"/api/v1/cases/{case['id']}/tasks/{task['id']}/decision"
        assert client.post(path, headers=headers, json={"plan_version": 0, "decision": "APPROVED"}).status_code == 422
        payload = {"plan_version": data["plan_version"], "decision": "APPROVED"}
        assert client.post(path, headers=headers, json=payload).json()["status"] == "APPROVED"
        assert client.post(path, headers=headers, json=payload).json()["status"] == "APPROVED"
        assert client.post(path, headers=headers, json={"plan_version": data["plan_version"], "decision": "REJECTED"}).status_code == 409
        fhir = client.get(f"/api/v1/cases/{case['id']}/tasks/{task['id']}/fhir", headers=headers).json()
        assert fhir["resourceType"] == "Task" and fhir["status"] == "requested"
        audits = client.get(f"/api/v1/cases/{case['id']}/audit", headers=headers).json()
        assert len([a for a in audits if a["event"] == "TASK_DECISION"]) == 1
        assert client.get("/api/v1/metrics", headers=headers).json()["approved_tasks"] >= 1
    finally:
        client.__exit__(None, None, None)


def test_role_access_and_tenant_isolation():
    client, admin = client_and_token()
    try:
        cases = client.get("/api/v1/cases", headers=admin).json()
        item = next(c for c in cases if c["reference"] == "CASE-1003")
        user = client.post("/api/v1/users", headers=admin, json={"username": "analysttest", "password": "long-analyst-password-123", "role": "analyst"})
        assert user.status_code in (201, 409)
        login = client.post("/api/v1/auth/token", json={"username": "analysttest", "password": "long-analyst-password-123"})
        token = {"Authorization": "Bearer " + login.json()["access_token"]}
        result = client.post(f"/api/v1/cases/{item['id']}/investigate", headers=token)
        assert result.status_code == 200
        task = result.json()["tasks"][0]
        r = client.post(f"/api/v1/cases/{item['id']}/tasks/{task['id']}/decision", headers=token,
                        json={"plan_version": result.json()["plan_version"], "decision": "APPROVED"})
        assert r.status_code == 403
        with SessionLocal() as db:
            other_user = db.scalar(select(User).where(User.username == "other-tenant"))
            if not other_user:
                db.add(User(username="other-tenant", password_hash=hash_password("other-tenant-pass-1234"),
                            tenant_id="other-hospital", role="supervisor"))
                db.commit()
        other = client.post("/api/v1/auth/token", json={"username": "other-tenant", "password": "other-tenant-pass-1234"})
        other_token = {"Authorization": "Bearer " + other.json()["access_token"]}
        assert client.get(f"/api/v1/cases/{item['id']}", headers=other_token).status_code == 404
        assert client.get("/api/v1/cases", headers=other_token).json() == []
    finally:
        client.__exit__(None, None, None)


def test_clean_case_never_claims_clinical_clearance():
    client, headers = client_and_token()
    try:
        case = next(c for c in client.get("/api/v1/cases", headers=headers).json() if c["reference"] == "CASE-1002")
        data = client.post(f"/api/v1/cases/{case['id']}/investigate", headers=headers).json()
        assert data["tasks"] == []
        assert data["status"] == "NO_FINDINGS"
        assert "not clinical clearance" in data["findings"][0]["description"]
    finally:
        client.__exit__(None, None, None)
