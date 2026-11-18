"""Thread-safe RunStore, SSE broadcaster, and SQLite/JSONL local persistence."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from dashboard.config import RUNS_DATA_DIR, RUNS_DB_PATH
from dashboard.models import (
    EnvironmentInfo,
    IngestEvent,
    LogLine,
    RunState,
    RunSummary,
    TestCaseState,
)


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class SSEBroadcaster:
    """Manages per-run asyncio SSE subscribers across sync/async boundaries."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[str, set[tuple[asyncio.AbstractEventLoop, asyncio.Queue[dict[str, Any]]]]] = {}

    def subscribe(self, run_id: str, loop: asyncio.AbstractEventLoop) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=2000)
        with self._lock:
            self._subscribers.setdefault(run_id, set()).add((loop, q))
        return q

    def unsubscribe(self, run_id: str, loop: asyncio.AbstractEventLoop, q: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            subs = self._subscribers.get(run_id)
            if subs:
                subs.discard((loop, q))
                if not subs:
                    self._subscribers.pop(run_id, None)

    def publish(self, run_id: str, event_name: str, data: dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subscribers.get(run_id, ()))
            # Also notify wildcard subscribers listening on "__all__" (e.g. for new runs)
            subs.extend(self._subscribers.get("__all__", ()))

        payload = {"event": event_name, "data": data}
        for loop, q in subs:
            if loop.is_closed():
                continue

            def _put(queue: asyncio.Queue[dict[str, Any]] = q, item: dict[str, Any] = payload) -> None:
                if queue.full():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                try:
                    queue.put_nowait(item)
                except asyncio.QueueFull:
                    pass

            loop.call_soon_threadsafe(_put)


class RunStore:
    """In-memory state store backed by SQLite metadata and per-run JSONL log files."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._runs: dict[str, RunState] = {}
        self._case_index: dict[str, dict[str, TestCaseState]] = {}
        self._log_seq: dict[str, int] = {}
        self._latest_run_id: str | None = None
        self.broadcaster = SSEBroadcaster()

        RUNS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._load_recent_runs()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(RUNS_DB_PATH), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    state_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _load_recent_runs(self, limit: int = 20) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT state_json FROM runs ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        for row in reversed(rows):
            try:
                state = RunState.model_validate_json(row["state_json"])
                # Recover stale running states after unexpected server shutdown
                if state.status == "running":
                    state.status = "stopped"
                    state.finished_at = state.finished_at or now_iso()
                self._runs[state.run_id] = state
                self._case_index[state.run_id] = {c.nodeid: c for c in state.cases}
                max_seq = max(
                    [l.seq for l in state.session_logs] + [l.seq for c in state.cases for l in c.logs],
                    default=0,
                )
                self._log_seq[state.run_id] = max_seq
                self._latest_run_id = state.run_id
            except Exception:
                continue

    def _persist_run_unlocked(self, run: RunState) -> None:
        state_json = run.model_dump_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (run_id, title, target, status, started_at, finished_at, state_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    title=excluded.title,
                    target=excluded.target,
                    status=excluded.status,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    state_json=excluded.state_json
                """,
                (
                    run.run_id,
                    run.title,
                    run.target,
                    run.status,
                    run.started_at,
                    run.finished_at,
                    state_json,
                ),
            )
            conn.commit()

    def _append_log_jsonl(self, run_id: str, log_line: LogLine) -> None:
        log_path = RUNS_DATA_DIR / f"{run_id}.logs.jsonl"
        try:
            with log_path.open("a", encoding="utf-8") as fp:
                fp.write(log_line.model_dump_json() + "\n")
        except Exception:
            pass

    def _recompute_summary_unlocked(self, run: RunState) -> RunSummary:
        total = len(run.cases)
        passed = sum(1 for c in run.cases if c.status == "passed")
        failed = sum(1 for c in run.cases if c.status in ("failed", "error"))
        skipped = sum(1 for c in run.cases if c.status == "skipped")
        running = sum(1 for c in run.cases if c.status == "running")
        pending = sum(1 for c in run.cases if c.status == "pending")
        completed = passed + failed + skipped
        pass_rate = round((passed / completed) * 100.0, 1) if completed > 0 else 0.0
        duration_sec = round(sum(c.duration or 0.0 for c in run.cases), 2)

        run.summary = RunSummary(
            total=total,
            completed=completed,
            passed=passed,
            failed=failed,
            skipped=skipped,
            running=running,
            pending=pending,
            pass_rate=pass_rate,
            duration_sec=duration_sec,
        )
        return run.summary

    def create_or_get_run(
        self,
        run_id: str,
        title: str = "QA 자동화 테스트 실행",
        target: str = "custom",
        environment: EnvironmentInfo | None = None,
    ) -> RunState:
        with self._lock:
            if run_id in self._runs:
                run = self._runs[run_id]
                if environment and not run.environment.hostname:
                    run.environment = environment
                return run

            run = RunState(
                run_id=run_id,
                title=title,
                target=target,
                status="running",
                started_at=now_iso(),
                environment=environment or EnvironmentInfo(),
            )
            self._runs[run_id] = run
            self._case_index[run_id] = {}
            self._log_seq[run_id] = 0
            self._latest_run_id = run_id
            self._persist_run_unlocked(run)
            self.broadcaster.publish(run_id, "run_start", run.model_dump())
            return run

    def apply_event(self, event: IngestEvent) -> None:
        with self._lock:
            p = event.payload
            run_id = event.run_id

            if event.event_type == "run_start":
                env_raw = p.get("environment") or {}
                env = EnvironmentInfo.model_validate(env_raw) if env_raw else EnvironmentInfo()
                run = self.create_or_get_run(
                    run_id=run_id,
                    title=p.get("title") or "QA 자동화 테스트 실행",
                    target=p.get("target") or "pytest",
                    environment=env,
                )
                run.status = "running"
                if env.hostname:
                    run.environment = env
                self._persist_run_unlocked(run)
                self.broadcaster.publish(run_id, "run_start", run.model_dump())
                return

            run = self._runs.get(run_id)
            if run is None:
                run = self.create_or_get_run(run_id=run_id)

            if event.event_type == "collection_ready":
                raw_cases = p.get("cases", [])
                cases = [TestCaseState.model_validate(item) for item in raw_cases]
                run.cases = cases
                self._case_index[run_id] = {c.nodeid: c for c in cases}
                summary = self._recompute_summary_unlocked(run)
                self._persist_run_unlocked(run)
                self.broadcaster.publish(
                    run_id,
                    "collection_ready",
                    {
                        "run_id": run_id,
                        "cases": [c.model_dump() for c in cases],
                        "summary": summary.model_dump(),
                    },
                )
                return

            if event.event_type == "case_start":
                nodeid = p.get("nodeid", "")
                case = self._case_index[run_id].get(nodeid)
                if case is None and p.get("case"):
                    case = TestCaseState.model_validate(p["case"])
                    run.cases.append(case)
                    self._case_index[run_id][nodeid] = case
                if case is not None:
                    case.status = "running"
                    case.started_at = event.timestamp
                    run.active_nodeid = nodeid
                    summary = self._recompute_summary_unlocked(run)
                    self.broadcaster.publish(
                        run_id,
                        "case_start",
                        {
                            "run_id": run_id,
                            "nodeid": nodeid,
                            "started_at": case.started_at,
                            "summary": summary.model_dump(),
                        },
                    )
                return

            if event.event_type == "log":
                seq = self._log_seq.get(run_id, 0) + 1
                self._log_seq[run_id] = seq
                nodeid = p.get("nodeid") or run.active_nodeid
                log_line = LogLine(
                    seq=seq,
                    timestamp=event.timestamp,
                    stream=p.get("stream", "stdout"),
                    level=p.get("level", "info"),
                    stage=p.get("stage"),
                    text=str(p.get("text", "")),
                    nodeid=nodeid,
                )
                if nodeid and nodeid in self._case_index[run_id]:
                    self._case_index[run_id][nodeid].logs.append(log_line)
                else:
                    run.session_logs.append(log_line)
                self._append_log_jsonl(run_id, log_line)
                self.broadcaster.publish(
                    run_id,
                    "log",
                    {"run_id": run_id, "log": log_line.model_dump()},
                )
                return

            if event.event_type == "case_finish":
                nodeid = p.get("nodeid", "")
                case = self._case_index[run_id].get(nodeid)
                if case is not None:
                    case.status = p.get("status", "passed")
                    case.duration = p.get("duration")
                    case.finished_at = event.timestamp
                    case.summary = p.get("summary", "")
                    case.error_message = p.get("error_message", "")
                if run.active_nodeid == nodeid:
                    run.active_nodeid = None
                summary = self._recompute_summary_unlocked(run)
                self._persist_run_unlocked(run)
                self.broadcaster.publish(
                    run_id,
                    "case_finish",
                    {
                        "run_id": run_id,
                        "nodeid": nodeid,
                        "status": case.status if case else p.get("status", "passed"),
                        "duration": case.duration if case else p.get("duration"),
                        "finished_at": event.timestamp,
                        "summary": case.summary if case else "",
                        "error_message": case.error_message if case else "",
                        "run_summary": summary.model_dump(),
                    },
                )
                return

            if event.event_type == "run_finish":
                run.status = p.get("status") or (
                    "failed" if run.summary.failed > 0 else "completed"
                )
                run.finished_at = event.timestamp
                run.active_nodeid = None
                summary = self._recompute_summary_unlocked(run)
                self._persist_run_unlocked(run)
                self.broadcaster.publish(
                    run_id,
                    "run_finish",
                    {
                        "run_id": run_id,
                        "status": run.status,
                        "finished_at": run.finished_at,
                        "summary": summary.model_dump(),
                    },
                )

    def get_run_snapshot(self, run_id: str) -> RunState | None:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            return run.model_copy(deep=True)

    def get_latest_run(self) -> RunState | None:
        with self._lock:
            if not self._latest_run_id:
                return None
            return self.get_run_snapshot(self._latest_run_id)

    def clear_runs(self) -> int:
        """Clears all non-running runs from memory, SQLite, and log files."""
        with self._lock:
            to_delete = [rid for rid, r in self._runs.items() if r.status != "running"]
            for rid in to_delete:
                self._runs.pop(rid, None)
                self._case_index.pop(rid, None)
                self._log_seq.pop(rid, None)
                for pattern in (f"{rid}.logs.jsonl", f"{rid}.proc.log"):
                    p = RUNS_DATA_DIR / pattern
                    if p.exists():
                        try:
                            p.unlink()
                        except Exception:
                            pass

            if self._latest_run_id in to_delete:
                remaining = sorted(self._runs.values(), key=lambda r: r.started_at, reverse=True)
                self._latest_run_id = remaining[0].run_id if remaining else None

            if to_delete:
                with self._connect() as conn:
                    placeholders = ",".join("?" for _ in to_delete)
                    conn.execute(f"DELETE FROM runs WHERE run_id IN ({placeholders})", to_delete)
                    conn.commit()

            self.broadcaster.publish(
                "__all__",
                "runs_cleared",
                {"active_run_id": self._latest_run_id},
            )
            return len(to_delete)

    def list_runs(self) -> list[dict[str, Any]]:
        with self._lock:
            runs = sorted(self._runs.values(), key=lambda r: r.started_at, reverse=True)
            return [
                {
                    "run_id": r.run_id,
                    "title": r.title,
                    "target": r.target,
                    "status": r.status,
                    "started_at": r.started_at,
                    "finished_at": r.finished_at,
                    "summary": r.summary.model_dump(),
                }
                for r in runs
            ]


run_store = RunStore()
