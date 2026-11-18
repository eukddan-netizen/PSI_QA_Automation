"""Zero-touch pytest plugin for real-time log & hierarchy streaming to the QA Dashboard."""

from __future__ import annotations

import ctypes
import inspect
import json
import os
import platform
import queue
import re
import signal
import socket
import sys
import threading
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

import httpx
import pytest

from dashboard.catalog_loader import catalog_registry
from dashboard.config import DEFAULT_DASHBOARD_URL

_current_nodeid: ContextVar[str | None] = ContextVar("psi_dashboard_nodeid", default=None)

_STAGE_RE = re.compile(r"^>*\s*\[([^\]]+)\]\s*(.*)$")


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _detect_env() -> dict[str, Any]:
    hostname = socket.gethostname()
    ip = ""
    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        pass
    is_admin = False
    try:
        is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        pass
    return {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "hostname": hostname,
        "ip": ip,
        "python_version": platform.python_version(),
        "is_admin": is_admin,
    }


def _classify_log_line(text: str, stream: str) -> tuple[str, str | None]:
    stripped = text.strip()
    stage = None
    m = _STAGE_RE.match(stripped)
    if m:
        stage = m.group(1).strip()

    if stream == "stderr" or any(tok in stripped for tok in ("AssertionError", "Traceback", "[오류]", "[실패]", "FAIL")):
        return "error", stage
    if any(tok in stripped for tok in ("[성공]", "[완료]", "통과", "PASS")):
        return "success", stage
    if any(tok in stripped for tok in ("[참고]", "[경고]", "WARN", "SKIP")):
        return "warn", stage
    if stage:
        return "step", stage
    return "info", stage


class _DashboardEmitter:
    """Background non-blocking batch sender to FastAPI /api/ingest/events."""

    def __init__(self, base_url: str, run_id: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.run_id = run_id
        self._queue: queue.Queue[dict[str, Any] | None] = queue.Queue(maxsize=10000)
        self._stop_event = threading.Event()
        self._disabled = False
        self._thread = threading.Thread(target=self._worker, name="psi-dashboard-emitter", daemon=True)
        self._thread.start()

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._disabled:
            return
        event = {
            "event_type": event_type,
            "run_id": self.run_id,
            "timestamp": _now_iso(),
            "payload": payload,
        }
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            pass

    def flush_and_close(self, timeout: float = 3.0) -> None:
        self._stop_event.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        self._thread.join(timeout=timeout)

    def _worker(self) -> None:
        client = httpx.Client(timeout=2.5)
        endpoint = f"{self.base_url}/api/ingest/events"
        try:
            while True:
                batch: list[dict[str, Any]] = []
                try:
                    item = self._queue.get(timeout=0.05)
                except queue.Empty:
                    if self._stop_event.is_set():
                        break
                    continue

                if item is None:
                    break
                batch.append(item)

                # Drain queued items up to 50 per HTTP batch
                while len(batch) < 50:
                    try:
                        nxt = self._queue.get_nowait()
                        if nxt is None:
                            self._stop_event.set()
                            break
                        batch.append(nxt)
                    except queue.Empty:
                        break

                try:
                    client.post(endpoint, json={"events": batch})
                except Exception:
                    # Never disrupt test execution if dashboard server is unreachable
                    pass
        finally:
            client.close()


class _TeeStream:
    """Line-buffered stdout/stderr tee that preserves terminal output and forwards lines."""

    def __init__(self, original: TextIO, stream_name: str, emitter: _DashboardEmitter) -> None:
        self._original = original
        self._stream_name = stream_name
        self._emitter = emitter
        self._buffer = ""
        self._lock = threading.Lock()

    def write(self, data: str) -> int:
        written = self._original.write(data)
        if not data:
            return written
        with self._lock:
            self._buffer += data
            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                self._emit_line(line.rstrip("\r"))
        return written

    def flush(self) -> None:
        self._original.flush()
        with self._lock:
            if self._buffer.strip():
                self._emit_line(self._buffer.rstrip("\r"))
                self._buffer = ""

    def _emit_line(self, line: str) -> None:
        if not line.strip():
            return
        level, stage = _classify_log_line(line, self._stream_name)
        self._emitter.emit(
            "log",
            {
                "nodeid": _current_nodeid.get(),
                "stream": self._stream_name,
                "level": level,
                "stage": stage,
                "text": line,
            },
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


class DashboardPytestPlugin:
    """Pytest plugin connecting existing tests to the live dashboard."""

    def __init__(self, emitter: _DashboardEmitter, title: str, target: str) -> None:
        self.emitter = emitter
        self.title = title
        self.target = target
        self._orig_stdout: TextIO | None = None
        self._orig_stderr: TextIO | None = None
        self._case_reports: dict[str, dict[str, Any]] = {}
        self._tokens: dict[str, Any] = {}

    def pytest_sessionstart(self, session: pytest.Session) -> None:
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, signal.default_int_handler)
        self.emitter.emit(
            "run_start",
            {
                "title": self.title,
                "target": self.target,
                "environment": _detect_env(),
            },
        )
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        sys.stdout = _TeeStream(self._orig_stdout, "stdout", self.emitter)  # type: ignore[assignment]
        sys.stderr = _TeeStream(self._orig_stderr, "stderr", self.emitter)  # type: ignore[assignment]

    def pytest_collection_modifyitems(self, session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:
        resume_file = os.environ.get("PSI_DASHBOARD_RESUME_FILE")
        if resume_file:
            resume_path = Path(resume_file)
            if resume_path.exists():
                try:
                    pending_nodeids = json.loads(resume_path.read_text(encoding="utf-8"))
                    if isinstance(pending_nodeids, list):
                        pending_set = set(pending_nodeids)
                        selected = [item for item in items if item.nodeid in pending_set]
                        deselected = [item for item in items if item.nodeid not in pending_set]
                        if deselected:
                            config.hook.pytest_deselected(items=deselected)
                        items[:] = selected
                except Exception:
                    pass

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        cases = []
        for item in session.items:
            doc = ""
            obj = getattr(item, "obj", None)
            if obj is not None:
                doc = inspect.getdoc(obj) or ""
            markers = [m.name for m in item.iter_markers()]
            meta = catalog_registry.resolve_nodeid(item.nodeid, docstring=doc, markers=markers)
            cases.append(
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
                }
            )
        self.emitter.emit("collection_ready", {"cases": cases})

    def pytest_runtest_logstart(self, nodeid: str, location: tuple[str, int | None, str]) -> None:
        self._case_reports[nodeid] = {"duration": 0.0, "outcome": None, "error_message": ""}
        self._tokens[nodeid] = _current_nodeid.set(nodeid)
        self.emitter.emit("case_start", {"nodeid": nodeid})

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        rec = self._case_reports.setdefault(report.nodeid, {"duration": 0.0, "outcome": None, "error_message": ""})
        rec["duration"] += float(getattr(report, "duration", 0.0) or 0.0)

        if report.when == "setup":
            if report.skipped:
                rec["outcome"] = "skipped"
                rec["error_message"] = _extract_short_error(report)
            elif report.failed:
                rec["outcome"] = "error"
                rec["error_message"] = _extract_short_error(report)
        elif report.when == "call":
            if report.passed:
                rec["outcome"] = "passed"
            elif report.skipped:
                rec["outcome"] = "skipped"
                rec["error_message"] = _extract_short_error(report)
            elif report.failed:
                rec["outcome"] = "failed"
                rec["error_message"] = _extract_short_error(report)
        elif report.when == "teardown":
            if report.failed and rec["outcome"] in (None, "passed"):
                rec["outcome"] = "error"
                rec["error_message"] = _extract_short_error(report)

    def pytest_runtest_logfinish(self, nodeid: str, location: tuple[str, int | None, str]) -> None:
        # Flush buffered prints before finishing the case
        for stream in (sys.stdout, sys.stderr):
            if isinstance(stream, _TeeStream):
                stream.flush()

        rec = self._case_reports.pop(nodeid, {"duration": 0.0, "outcome": "passed", "error_message": ""})
        outcome = rec["outcome"] or "passed"
        duration = round(float(rec["duration"]), 3)
        err = rec["error_message"]
        summary = _build_case_summary(outcome, duration, err)

        self.emitter.emit(
            "case_finish",
            {
                "nodeid": nodeid,
                "status": outcome,
                "duration": duration,
                "summary": summary,
                "error_message": err,
            },
        )
        token = self._tokens.pop(nodeid, None)
        if token is not None:
            _current_nodeid.reset(token)

    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        for stream in (sys.stdout, sys.stderr):
            if isinstance(stream, _TeeStream):
                stream.flush()

        status = "completed" if exitstatus == 0 else ("stopped" if exitstatus == 2 else "failed")
        self.emitter.emit("run_finish", {"status": status, "exit_code": int(exitstatus)})

        if self._orig_stdout is not None:
            sys.stdout = self._orig_stdout
        if self._orig_stderr is not None:
            sys.stderr = self._orig_stderr

        self.emitter.flush_and_close(timeout=3.0)


def _extract_short_error(report: pytest.TestReport) -> str:
    longrepr = getattr(report, "longrepr", None)
    if longrepr is None:
        return ""
    try:
        # pytest ReprExceptionInfo has reprcrash
        crash = getattr(longrepr, "reprcrash", None)
        if crash and getattr(crash, "message", None):
            return str(crash.message).strip()
    except Exception:
        pass
    text = str(getattr(report, "longreprtext", "") or longrepr)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in reversed(lines):
        if ln.startswith("E   "):
            return ln[4:].strip()
    return lines[-1] if lines else ""


def _build_case_summary(outcome: str, duration: float, error_message: str) -> str:
    if outcome == "passed":
        return f"정상 검증 완료함 ({duration:.2f}초)"
    if outcome == "skipped":
        reason = error_message or "실행 조건 미충족"
        return f"점검 제외됨: {reason}"
    reason = error_message.splitlines()[0] if error_message else "검증 조건 불일치"
    return f"오류 발생: {reason}"


def register_dashboard_hooks(parser: pytest.Parser) -> None:
    parser.addoption(
        "--dashboard",
        action="store_true",
        default=False,
        help="로컬 QA 대시보드로 테스트 실행 로그 및 결과를 실시간 스트리밍합니다.",
    )
    parser.addoption(
        "--dashboard-url",
        action="store",
        default=None,
        help="대시보드 백엔드 URL (기본: http://127.0.0.1:8000)",
    )


def configure_dashboard_plugin(config: pytest.Config) -> None:
    enabled = bool(config.getoption("--dashboard", False)) or bool(os.environ.get("PSI_DASHBOARD_RUN_ID"))
    if not enabled:
        return

    base_url = (
        config.getoption("--dashboard-url", None)
        or os.environ.get("PSI_DASHBOARD_URL")
        or DEFAULT_DASHBOARD_URL
    )
    run_id = os.environ.get("PSI_DASHBOARD_RUN_ID") or (
        datetime.now().strftime("run_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
    )
    target_opt = config.getoption("-m", None) or os.environ.get("PSI_DASHBOARD_TARGET") or "pytest"
    title = os.environ.get("PSI_DASHBOARD_TITLE") or f"QA 자동화 실행 ({target_opt})"

    emitter = _DashboardEmitter(base_url=base_url, run_id=run_id)
    plugin = DashboardPytestPlugin(emitter=emitter, title=title, target=str(target_opt))
    config.pluginmanager.register(plugin, name="psi_dashboard_plugin")
