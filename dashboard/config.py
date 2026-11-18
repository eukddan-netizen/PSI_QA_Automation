"""Configuration constants and runtime paths for the QA Dashboard."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
APP_CATALOG_PATH = TESTS_DIR / "app_checks" / "catalog_app.yaml"
SECURITY_CATALOG_PATH = TESTS_DIR / "security_checks" / "catalog.yaml"

DASHBOARD_DIR = Path(__file__).resolve().parent
STATIC_DIR = DASHBOARD_DIR / "static"
RUNS_DATA_DIR = PROJECT_ROOT / "reports" / "dashboard_runs"
RUNS_DB_PATH = RUNS_DATA_DIR / "runs.db"

DEFAULT_HOST = os.environ.get("PSI_DASHBOARD_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("PSI_DASHBOARD_PORT", "8000"))
DEFAULT_DASHBOARD_URL = os.environ.get("PSI_DASHBOARD_URL", f"http://{DEFAULT_HOST}:{DEFAULT_PORT}")

VENV_PYTEST_PATH = PROJECT_ROOT / ".venv" / "Scripts" / "pytest.exe"
VENV_PYTHON_PATH = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
