"""
Application Configuration Settings.
"""

import os

# Database Configuration
# Default to local SQLite for rapid test execution if PostgreSQL is unavailable,
# but support standard Postgres URI in Docker Compose or Production.
DEFAULT_SQLITE_PATH = os.environ.get("SQLITE_PATH", "app.db")

DATABASE_URL = os.environ.get(
    "DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}"
)

# API Server Config
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
FHIR_API_BASE_URL = os.environ.get("FHIR_API_BASE_URL", "http://localhost:8000")

# App Info
APP_NAME = "Clinical Data & Principal Diagnosis Review System"
APP_VERSION = "1.0.0"
