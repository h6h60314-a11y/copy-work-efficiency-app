import hashlib
from supabase import create_client
import streamlit as st


# ======================
# Supabase client
# ======================
def _sb():
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in secrets")

    return create_client(url, key)


# ======================
# Utils
# ======================
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ======================
# Storage
# ======================
def upload_export_bytes(*, content: bytes, object_path: str) -> str:
    """
    Upload Excel bytes to Supabase Storage
    Return object_path for DB reference
    """
    sb = _sb()
    bucket = st.secrets.get("SUPABASE_BUCKET", "work-efficiency-exports")

    sb.storage.from_(bucket).upload(
        object_path,
        content,
        file_options={
            "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        },
        upsert=True,
    )
    return object_path


# ======================
# DB: audit_runs
# ======================
def insert_audit_run(payload: dict) -> dict:
    """
    Insert one audit record into public.audit_runs
    """
    sb = _sb()

    res = (
        sb.schema("public")
        .table("audit_runs")
        .insert(payload)
        .execute()
    )

    if res.data:
        return res.data[0]
    return {}
