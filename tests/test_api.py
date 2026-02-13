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
        assert resp.status_code in (400, 422)

    def test_upload_valid_pdf(self, client: TestClient, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF-1.4 fake content")
        with open(f, "rb") as fp:
            resp = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", fp, "application/pdf")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "doc_id" in data
        assert data["filename"] == "test.pdf"
        assert data["size_bytes"] > 0
        assert "path" in data


class TestDocumentList:
    def test_list_documents(self, client: TestClient):
        resp = client.get("/api/v1/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert "documents" in data
        assert isinstance(data["documents"], list)


class TestAnalysisStart:
    def test_start_file_not_found(self, client: TestClient):
        resp = client.post(
            "/api/v1/analysis/start",
            json={"file_path": "/nonexistent/file.pdf"},
        )
        assert resp.status_code == 404

    def test_start_returns_job_id(self, client: TestClient, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4 fake")
        resp = client.post(
            "/api/v1/analysis/start",
            json={"file_path": str(f)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "started"


class TestAnalysisStatus:
    def test_status_job_not_found(self, client: TestClient):
        resp = client.get("/api/v1/analysis/nonexistent/status")
        assert resp.status_code == 404


class TestReportsEndpoints:
    def test_reports_list(self, client: TestClient):
        resp = client.get("/api/v1/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert "reports" in data
        assert isinstance(data["reports"], list)

    def test_report_json_not_found(self, client: TestClient):
        resp = client.get("/api/v1/reports/nonexistent-id/json")
        assert resp.status_code == 404

    def test_report_pdf_not_found(self, client: TestClient):
        resp = client.get("/api/v1/reports/nonexistent-id/pdf")
        assert resp.status_code == 404

    def test_report_detail_not_found(self, client: TestClient):
        resp = client.get("/api/v1/reports/nonexistent-id")
        assert resp.status_code == 404


class TestAuditEndpoints:
    def test_recent_audit(self, client: TestClient):
        resp = client.get("/api/v1/audit/recent")
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data
        assert isinstance(data["records"], list)

    def test_recent_audit_with_limit(self, client: TestClient):
        resp = client.get("/api/v1/audit/recent", params={"limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data

    def test_audit_by_document(self, client: TestClient):
        resp = client.get("/api/v1/audit/document/some-doc-id")
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data
        assert isinstance(data["records"], list)

    def test_audit_by_user(self, client: TestClient):
        resp = client.get("/api/v1/audit/user/test-user")
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data
        assert isinstance(data["records"], list)

