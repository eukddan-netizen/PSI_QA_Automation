"""Subprocess manager allowing the dashboard UI to trigger and stop pytest runs."""

from __future__ import annotations

import ctypes
import os
import subprocess
import threading
import uuid
from datetime import datetime
from typing import Any

from dashboard.config import DEFAULT_DASHBOARD_URL, PROJECT_ROOT, RUNS_DATA_DIR, VENV_PYTEST_PATH
from dashboard.models import EnvironmentInfo, IngestEvent, StartRunRequest
from dashboard.store import now_iso, run_store


def is_process_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


class RunnerManager:
    """Starts and tracks a local pytest process streaming into RunStore."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_proc: subprocess.Popen[bytes] | None = None
        self._active_run_id: str | None = None

    def is_running(self) -> bool:
        with self._lock:
            return self._active_proc is not None and self._active_proc.poll() is None

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            running = self._active_proc is not None and self._active_proc.poll() is None
            return {
                "is_running": running,
                "active_run_id": self._active_run_id if running else None,
                "is_admin": is_process_admin(),
            }

    def start_run(self, req: StartRunRequest) -> dict[str, Any]:
        with self._lock:
            if self._active_proc is not None and self._active_proc.poll() is None:
                raise RuntimeError(f"이미 실행 중인 테스트({self._active_run_id})가 있습니다.")

            if not VENV_PYTEST_PATH.exists():
                raise FileNotFoundError(f"pytest 실행 파일을 찾을 수 없습니다: {VENV_PYTEST_PATH}")

            run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
            title = req.title or f"QA 자동화 실행 ({req.target})"

            cmd = [str(VENV_PYTEST_PATH), "--dashboard", "-s"]
            if req.markers:
                cmd.extend(["-m", req.markers])
            if req.keyword:
                cmd.extend(["-k", req.keyword])
            if req.paths:
                cmd.extend(req.paths)

            env = os.environ.copy()
            env["PSI_DASHBOARD_URL"] = DEFAULT_DASHBOARD_URL
            env["PSI_DASHBOARD_RUN_ID"] = run_id
            env["PSI_DASHBOARD_TITLE"] = title
            env["PSI_DASHBOARD_TARGET"] = req.target
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"

            run_store.create_or_get_run(
                run_id=run_id,
                title=title,
                target=req.target,
                environment=EnvironmentInfo(is_admin=is_process_admin()),
            )

            # Avoid stdout=PIPE so spawned Windows GUI child apps (taKeeper.exe) never keep pipe handles open.
            RUNS_DATA_DIR.mkdir(parents=True, exist_ok=True)
            proc_log_path = RUNS_DATA_DIR / f"{run_id}.proc.log"
            log_fp = proc_log_path.open("wb")
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(PROJECT_ROOT),
                    env=env,
                    stdout=log_fp,
                    stderr=subprocess.STDOUT,
                )
            finally:
                log_fp.close()

            self._active_proc = proc
            self._active_run_id = run_id

            run_store.broadcaster.publish(
                "__all__",
                "runner_status",
                {
                    "is_running": True,
                    "active_run_id": run_id,
                    "is_admin": is_process_admin(),
                },
            )

            watcher = threading.Thread(
                target=self._watch_process,
                args=(proc, run_id),
                daemon=True,
            )
            watcher.start()

            return {"run_id": run_id, "title": title, "command": " ".join(cmd)}

    def stop_run(self, run_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            if self._active_proc is None or self._active_proc.poll() is not None:
                self._active_proc = None
                self._active_run_id = None
                return {
                    "stopped": False,
                    "already_finished": True,
                    "runner": {
                        "is_running": False,
                        "active_run_id": None,
                        "is_admin": is_process_admin(),
                    },
                }

            if run_id and run_id != self._active_run_id:
                return {
                    "stopped": False,
                    "already_finished": True,
                    "runner": {
                        "is_running": True,
                        "active_run_id": self._active_run_id,
                        "is_admin": is_process_admin(),
                    },
                }

            target_run_id = self._active_run_id
            try:
                self._active_proc.terminate()
            except Exception:
                pass

        if target_run_id:
            run_store.apply_event(
                IngestEvent(
                    event_type="log",
                    run_id=target_run_id,
                    timestamp=now_iso(),
                    payload={
                        "stream": "system",
                        "level": "warn",
                        "text": "사용자 요청에 의해 테스트 실행 중단 신호가 전송되었습니다.",
                    },
                )
            )
        return {
            "stopped": True,
            "already_finished": False,
            "run_id": target_run_id,
            "runner": self.get_status(),
        }

    def _watch_process(self, proc: subprocess.Popen[bytes], run_id: str) -> None:
        exit_code = proc.wait()

        with self._lock:
            if self._active_proc is proc:
                self._active_proc = None
                self._active_run_id = None

        run_store.broadcaster.publish(
            "__all__",
            "runner_status",
            {
                "is_running": False,
                "active_run_id": None,
                "is_admin": is_process_admin(),
            },
        )

        snapshot = run_store.get_run_snapshot(run_id)
        if snapshot and snapshot.status == "running":
            final_status = "completed" if exit_code == 0 else ("stopped" if exit_code < 0 else "failed")
            run_store.apply_event(
                IngestEvent(
                    event_type="run_finish",
                    run_id=run_id,
                    timestamp=now_iso(),
                    payload={"status": final_status, "exit_code": exit_code},
                )
            )


runner_manager = RunnerManager()
