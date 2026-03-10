"""
WCAG Audit Agent - Configuration
Loads ALL settings from .env file in the project root.
Every module imports from here instead of reading env vars directly.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ─── Load .env from project root ─────────────────────────
# Find the project root (where .env lives)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)
else:
    print(f"⚠️  No .env file found at: {ENV_PATH}")
    print(f"   Copy .env.example to .env and fill in your values.")
    print(f"   Example: copy .env.example .env")


# ─── Gemini / Google GenAI Settings ──────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Legacy Vertex AI settings (kept for backward compat)
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")

# Resolve credentials path relative to project root
_cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
if _cred_path and not os.path.isabs(_cred_path):
    _cred_path = str(PROJECT_ROOT / _cred_path)

GOOGLE_APPLICATION_CREDENTIALS = _cred_path

# CRITICAL: Set the env var so Google Cloud SDK auto-picks it up
if GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

# If project ID not in .env, try reading from service account JSON
if not GCP_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
    try:
        import json
        with open(GOOGLE_APPLICATION_CREDENTIALS) as f:
            GCP_PROJECT_ID = json.load(f).get("project_id", "")
    except Exception:
        pass


# ─── Crawler Settings ────────────────────────────────────
MAX_PAGES = int(os.getenv("MAX_PAGES", "20"))
CRAWL_TIMEOUT_MS = int(os.getenv("CRAWL_TIMEOUT_MS", "30000"))
HEADLESS_BROWSER = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"


# ─── Pinecone (Step 4) ───────────────────────────────────
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "wcag-knowledge")


# ─── Anthropic (Optional) ────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


# ─── Database & Storage (Step 6+) ────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")


# ─── Validation ──────────────────────────────────────────
def validate_vertex_ai():
    """Check if Vertex AI credentials are properly configured."""
    errors = []

    if not GCP_PROJECT_ID:
        errors.append("GCP_PROJECT_ID is not set in .env")

    if not GOOGLE_APPLICATION_CREDENTIALS:
        errors.append("GOOGLE_APPLICATION_CREDENTIALS is not set in .env")
    elif not os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
        errors.append(f"Credentials file not found: {GOOGLE_APPLICATION_CREDENTIALS}")

    if errors:
        print("\n❌ Vertex AI configuration errors:")
        for e in errors:
            print(f"   • {e}")
        print(f"\n   Fix your .env file at: {ENV_PATH}")
        print(f"   Credentials resolved to: {GOOGLE_APPLICATION_CREDENTIALS}")
        sys.exit(1)

    return True


def print_config():
    """Print current configuration for debugging."""
    cred_status = "✅ Found" if os.path.exists(GOOGLE_APPLICATION_CREDENTIALS) else "❌ NOT FOUND"
    print(f"  GCP Project:    {GCP_PROJECT_ID}")
    print(f"  GCP Region:     {GCP_REGION}")
    print(f"  Gemini Model:   {GEMINI_MODEL}")
    print(f"  Credentials:    {GOOGLE_APPLICATION_CREDENTIALS} ({cred_status})")
    print(f"  .env loaded:    {ENV_PATH}")
