from fastapi.testclient import TestClient

import src.api.app as api_app


class StubFacade:
    def health(self):
        return {"status": "ok", "llm_configured": False, "browser": {}}

    def list_jobs(self):
        return []

    def get_job(self, job_id):
        return None

    def cancel_job(self, job_id):
        return False


def test_workflow_api_health_uses_facade(monkeypatch):
    monkeypatch.setattr(api_app, "facade", StubFacade())
    client = TestClient(api_app.app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
