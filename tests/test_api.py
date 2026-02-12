"""Tests for the FastAPI application endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "environment" in data


class TestDocumentUpload:
    def test_upload_no_file_returns_422(self, client: TestClient):
        resp = client.post("/api/v1/documents/upload")
        assert resp.status_code == 422

    def test_upload_unsupported_format(self, client: TestClient, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        with open(f, "rb") as fp:
            resp = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.txt", fp, "text/plain")},
            )
        # Should reject unsupported format
        assert resp.status_code in (400, 422)


class TestReportsEndpoints:
    def test_reports_list(self, client: TestClient):
        resp = client.get("/api/v1/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert "reports" in data
        assert isinstance(data["reports"], list)

    def test_report_not_found(self, client: TestClient):
        resp = client.get("/api/v1/reports/nonexistent-id/json")
        assert resp.status_code == 404


class TestAuditEndpoint:
    def test_recent_audit(self, client: TestClient):
        resp = client.get("/api/v1/audit/recent")
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data
        assert isinstance(data["records"], list)
