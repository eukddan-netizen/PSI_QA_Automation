"""Subprocess-isolated pytest test-case collector and in-memory cache for the dashboard sidebar."""

from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

from dashboard.catalog_loader import catalog_registry
from dashboard.config import PROJECT_ROOT, VENV_PYTHON_PATH

_DOMAIN_ORDER = {"app_checks": 0, "security_checks": 1, "other": 2}


class _CatalogCollectPlugin:
    """Lightweight pytest plugin used only during --collect-only to extract resolved case metadata."""

    def __init__(self) -> None:
        self.cases: list[dict[str, Any]] = []

    def pytest_collection_finish(self, session: Any) -> None:
        catalog_registry.reload()
        raw: list[tuple[int, dict[str, Any]]] = []
        for idx, item in enumerate(session.items):
            doc = ""
            obj = getattr(item, "obj", None)
            if obj is not None:
                doc = inspect.getdoc(obj) or ""
            markers = [m.name for m in item.iter_markers()]
            meta = catalog_registry.resolve_nodeid(item.nodeid, docstring=doc, markers=markers)
            raw.append(
                (
                    idx,
                    {
                        "nodeid": item.nodeid,
                        "tc_id": meta["tc_id"],
                        "id": meta["id"],
                        "title": meta["title"],
                        "docstring": doc,
                        "domain": meta["domain"],
                        "domain_title": meta["domain_title"],
                        "category_id": meta["category_id"],
                        "category_title": meta["category_title"],
                        "subcategory_id": meta["subcategory_id"],
                        "subcategory_title": meta["subcategory_title"],
                        "markers": markers,
                        "status": "pending",
                        "duration": None,
                        "started_at": None,
                        "finished_at": None,
                        "summary": "",
                        "error_message": "",
                        "logs": [],
                    },
                )
            )

        raw.sort(
            key=lambda pair: (
                _DOMAIN_ORDER.get(pair[1]["domain"], 99),
                pair[1]["category_id"] or "",
                pair[1]["subcategory_id"] or "",
                pair[0],
            )
        )
        self.cases = [entry for _, entry in raw]


def collect_cases_to_file(out_path: Path) -> int:
    """Runs pytest --collect-only in-process (intended for subprocess CLI invocation)."""
    import pytest

    plugin = _CatalogCollectPlugin()
    # Ensure DashboardPytestPlugin does not activate during pure catalog collection
    os.environ.pop("PSI_DASHBOARD_RUN_ID", None)
    exit_code = pytest.main(
        ["--collect-only", "-q", "--no-header", "--no-summary"],
        plugins=[plugin],
    )
    out_path.write_text(json.dumps(plugin.cases, ensure_ascii=False), encoding="utf-8")
    return int(exit_code)


class CatalogCaseCache:
    """Caches collected pytest test cases in memory with thread-safe single-flight refresh."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cases: list[dict[str, Any]] | None = None
        self._last_error: str | None = None

    def _collect_subprocess(self) -> list[dict[str, Any]]:
        python_exe = str(VENV_PYTHON_PATH) if VENV_PYTHON_PATH.exists() else sys.executable
        env = os.environ.copy()
        env.pop("PSI_DASHBOARD_RUN_ID", None)
        env.pop("PSI_DASHBOARD_RESUME_FILE", None)
        env["PYTHONIOENCODING"] = "utf-8"

        with tempfile.TemporaryDirectory(prefix="psi_catalog_") as tmp_dir:
            out_file = Path(tmp_dir) / "cases.json"
            proc = subprocess.run(
                [python_exe, "-m", "dashboard.case_collector", str(out_file)],
                cwd=str(PROJECT_ROOT),
                env=env,
                capture_output=True,
                timeout=45,
            )
            if out_file.exists():
                data = json.loads(out_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            stderr_text = proc.stderr.decode("utf-8", errors="replace").strip()
            stdout_text = proc.stdout.decode("utf-8", errors="replace").strip()
            detail = stderr_text or stdout_text or f"exit_code={proc.returncode}"
            raise RuntimeError(f"테스트 목록 수집에 실패했습니다: {detail[:300]}")

    def get_cases(self, *, refresh: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            if not refresh and self._cases is not None:
                return list(self._cases)
            try:
                collected = self._collect_subprocess()
                self._cases = collected
                self._last_error = None
                return list(collected)
            except Exception as exc:
                self._last_error = str(exc)
                if self._cases is not None:
                    return list(self._cases)
                raise

    def warmup_async(self) -> None:
        def _run() -> None:
            try:
                self.get_cases(refresh=False)
            except Exception:
                pass

        threading.Thread(target=_run, name="psi-catalog-warmup", daemon=True).start()


catalog_case_cache = CatalogCaseCache()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(2)
    target_path = Path(sys.argv[1])
    code = collect_cases_to_file(target_path)
    # pytest returns 0 (tests collected) or 5 (no tests collected); both produce valid JSON
    sys.exit(0 if code in (0, 5) else code)
