"""Streamlit frontend for the Learning Content Compliance Intelligence System."""

import json
import time
from pathlib import Path

import requests
import streamlit as st

# ── Configuration ────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="LRA — Compliance Intelligence",
    page_icon="📋",
    layout="wide",
)


# ── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title("📋 LRA")
st.sidebar.markdown("**Learning Content Compliance Intelligence System**")
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Dashboard", "📤 Upload & Analyse", "📊 Reports", "🔍 Audit Log"],
)


# ── Helper functions ─────────────────────────────────────────────────────────

def api_get(endpoint: str, params: dict = None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def api_post(endpoint: str, **kwargs):
    try:
        r = requests.post(f"{API_BASE}{endpoint}", timeout=300, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


# ── Dashboard ────────────────────────────────────────────────────────────────

if page == "🏠 Dashboard":
    st.title("Dashboard")

    col1, col2, col3 = st.columns(3)

    # Documents count
    docs = api_get("/api/v1/documents")
    doc_count = len(docs.get("documents", [])) if docs else 0
    col1.metric("📄 Documents Uploaded", doc_count)

    # Reports count
    reports = api_get("/api/v1/reports")
    report_count = len(reports.get("reports", [])) if reports else 0
    col2.metric("📊 Reports Generated", report_count)

    # Health
    health = api_get("/health")
    col3.metric("🟢 Status", health.get("status", "unknown") if health else "offline")

    st.markdown("---")
    st.subheader("Recent Reports")
    if reports and reports.get("reports"):
        for r in reports["reports"][:5]:
            st.markdown(f"- `{r['report_id']}` — {r['filename']}")
    else:
        st.info("No reports yet. Upload a document to get started.")


# ── Upload & Analyse ─────────────────────────────────────────────────────────

elif page == "📤 Upload & Analyse":
    st.title("Upload & Analyse Document")

    uploaded_file = st.file_uploader(
        "Upload a learning document",
        type=["pdf", "docx", "pptx", "xlsx"],
    )

    if uploaded_file is not None:
        st.success(f"File: **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")

        if st.button("🚀 Start Analysis", type="primary"):
            # Upload file
            with st.spinner("Uploading..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                upload_result = api_post("/api/v1/documents/upload", files=files)

            if upload_result:
                st.info(f"Uploaded: {upload_result['filename']}")

                # Start analysis
                with st.spinner("Starting analysis pipeline..."):
                    analysis_result = api_post(
                        "/api/v1/analysis/start",
                        params={"file_path": upload_result["path"]},
                    )

                if analysis_result:
                    job_id = analysis_result["job_id"]
                    st.info(f"Job started: `{job_id}`")

                    # Poll for progress
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    while True:
                        time.sleep(2)
                        status = api_get(f"/api/v1/analysis/{job_id}/status")
                        if not status:
                            break

                        progress = status.get("progress", 0)
                        stage = status.get("stage", "unknown")
                        progress_bar.progress(int(progress))
                        status_text.text(f"Stage: {stage} — {progress:.0f}%")

                        if stage == "completed":
                            st.balloons()
                            st.success(
                                f"✅ Analysis complete! Report ID: `{status.get('report_id')}`"
                            )
                            break
                        elif stage == "failed":
                            st.error(f"❌ Pipeline failed: {status.get('errors')}")
                            break


# ── Reports ──────────────────────────────────────────────────────────────────

elif page == "📊 Reports":
    st.title("Compliance Reports")

    reports = api_get("/api/v1/reports")
    if reports and reports.get("reports"):
        for r in reports["reports"]:
            rid = r["report_id"]
            with st.expander(f"📋 Report: {rid}"):
                col1, col2 = st.columns(2)
                col1.markdown(
                    f"[📥 Download JSON]({API_BASE}/api/v1/reports/{rid}/json)"
                )
                col2.markdown(
                    f"[📥 Download PDF]({API_BASE}/api/v1/reports/{rid}/pdf)"
                )

                # Try to load and display the report
                json_path = Path(f"data/reports/report_{rid}.json")
                if json_path.exists():
                    data = json.loads(json_path.read_text())
                    comp = data.get("overall_compliance", {})
                    st.metric("Compliance Score", f"{comp.get('score', 0)}%")

                    c1, c2, c3 = st.columns(3)
                    c1.metric("✅ Passed", comp.get("passed", 0))
                    c2.metric("❌ Failed", comp.get("failed", 0))
                    c3.metric("⚠️ Partial", comp.get("partial", 0))

                    if data.get("executive_summary"):
                        st.markdown("**Executive Summary**")
                        st.write(data["executive_summary"])
    else:
        st.info("No reports available yet.")


# ── Audit Log ────────────────────────────────────────────────────────────────

elif page == "🔍 Audit Log":
    st.title("Audit Trail")

    records = api_get("/api/v1/audit/recent", params={"limit": 50})
    if records and records.get("records"):
        for rec in records["records"]:
            with st.expander(
                f"🕐 {rec.get('timestamp', '')} — {rec.get('filename', '')} "
                f"(Score: {rec.get('score', 'N/A')}%)"
            ):
                st.json(
                    {
                        k: v
                        for k, v in rec.items()
                        if k != "result_json"
                    }
                )
    else:
        st.info("No audit records found.")
