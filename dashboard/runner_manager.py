"""Subprocess manager allowing the dashboard UI to trigger and stop pytest runs."""

from __future__ import annotations

import ctypes
import json
import os
import signal
import subprocess
import sys
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
        self._stop_requested_run_id: str | None = None

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

    def _launch_pytest_unlocked(
        self,
        *,
        run_id: str,
        title: str,
        target: str,
        cmd: list[str],
        append_log: bool = False,
        extra_env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        env = os.environ.copy()
        env["PSI_DASHBOARD_URL"] = DEFAULT_DASHBOARD_URL
        env["PSI_DASHBOARD_RUN_ID"] = run_id
        env["PSI_DASHBOARD_TITLE"] = title
        env["PSI_DASHBOARD_TARGET"] = target
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        if extra_env:
            env.update(extra_env)

        # Avoid stdout=PIPE so spawned Windows GUI child apps (taKeeper.exe) never keep pipe handles open.
        RUNS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        proc_log_path = RUNS_DATA_DIR / f"{run_id}.proc.log"
        log_fp = proc_log_path.open("ab" if append_log else "wb")
        popen_kwargs: dict[str, Any] = {}
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                env=env,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                **popen_kwargs,
            )
        finally:
            log_fp.close()

        self._active_proc = proc
        self._active_run_id = run_id
        self._stop_requested_run_id = None

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

    def start_run(self, req: StartRunRequest) -> dict[str, Any]:
        with self._lock:
            if self._active_proc is not None and self._active_proc.poll() is None:
                raise RuntimeError(f"이미 실행 중인 테스트({self._active_run_id})가 있습니다.")

            if not VENV_PYTEST_PATH.exists():
                raise FileNotFoundError(f"pytest 실행 파일을 찾을 수 없습니다: {VENV_PYTEST_PATH}")

            requested_title = req.title or f"QA 자동화 실행 ({req.target})"

            target_run_id: str | None = None
            if req.accumulate:
                if req.run_id and run_store.has_run(req.run_id):
                    target_run_id = req.run_id
                else:
                    target_run_id = run_store.get_latest_run_id()

            if target_run_id:
                run_id = target_run_id
                run_state = run_store.begin_append_run(
                    run_id=run_id,
                    title=requested_title,
                    target=req.target,
                    environment=EnvironmentInfo(is_admin=is_process_admin()),
                )
            else:
                run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
                run_state = run_store.create_or_get_run(
                    run_id=run_id,
                    title=requested_title,
                    target=req.target,
                    environment=EnvironmentInfo(is_admin=is_process_admin()),
                )

            cmd = [str(VENV_PYTEST_PATH), "--dashboard", "-s"]
            if req.markers:
                cmd.extend(["-m", req.markers])
            if req.keyword:
                cmd.extend(["-k", req.keyword])
            if req.paths:
                cmd.extend(req.paths)

            return self._launch_pytest_unlocked(
                run_id=run_id,
                title=run_state.title,
                target=req.target,
                cmd=cmd,
                append_log=bool(target_run_id),
            )

    def resume_run(self, run_id: str) -> dict[str, Any]:
        """Resumes a stopped/interrupted run by executing only its remaining pending test cases."""
        with self._lock:
            if self._active_proc is not None and self._active_proc.poll() is None:
                raise RuntimeError(f"이미 실행 중인 테스트({self._active_run_id})가 있습니다.")

            if not VENV_PYTEST_PATH.exists():
                raise FileNotFoundError(f"pytest 실행 파일을 찾을 수 없습니다: {VENV_PYTEST_PATH}")

            snap = run_store.get_run_snapshot(run_id)
            if snap is None:
                raise KeyError(f"실행 이력을 찾을 수 없습니다: {run_id}")

            pending_nodeids = [c.nodeid for c in snap.cases if c.status == "pending"]
            if not pending_nodeids:
                raise RuntimeError("이어서 진행할 미완료 대기 테스트 항목이 없습니다.")

            file_paths = list(dict.fromkeys(nid.split("::", 1)[0] for nid in pending_nodeids))
            RUNS_DATA_DIR.mkdir(parents=True, exist_ok=True)
            resume_file = RUNS_DATA_DIR / f"{run_id}.resume.json"
            resume_file.write_text(json.dumps(pending_nodeids, ensure_ascii=False), encoding="utf-8")

            run_state = run_store.begin_resume_run(
                run_id=run_id,
                pending_count=len(pending_nodeids),
                environment=EnvironmentInfo(is_admin=is_process_admin()),
            )

            cmd = [str(VENV_PYTEST_PATH), "--dashboard", "-s", *file_paths]
            return self._launch_pytest_unlocked(
                run_id=run_id,
                title=run_state.title,
                target=run_state.target,
                cmd=cmd,
                append_log=True,
                extra_env={"PSI_DASHBOARD_RESUME_FILE": str(resume_file)},
            )

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
            proc = self._active_proc
            already_stopping = self._stop_requested_run_id == target_run_id
            self._stop_requested_run_id = target_run_id

            if sys.platform == "win32" and not already_stopping:
                try:
                    proc.send_signal(signal.CTRL_BREAK_EVENT)
                except Exception:
                    try:
                        proc.terminate()
                    except Exception:
                        pass

                def _force_kill_fallback(target_proc: subprocess.Popen[bytes]) -> None:
                    try:
                        target_proc.wait(timeout=8.0)
                    except subprocess.TimeoutExpired:
                        try:
                            if target_proc.poll() is None:
                                target_proc.terminate()
                        except Exception:
                            pass

                threading.Thread(target=_force_kill_fallback, args=(proc,), daemon=True).start()
            else:
                try:
                    proc.terminate()
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
                        "text": (
                            "테스트 강제 종료 신호를 전송했습니다."
                            if already_stopping
                            else "사용자 요청에 의해 중단 신호를 전송했습니다. 현재 테스트 원복(teardown) 후 종료합니다."
                        ),
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
            was_stopped = self._stop_requested_run_id == run_id
            if self._stop_requested_run_id == run_id:
                self._stop_requested_run_id = None
            if self._active_proc is proc:
                self._active_proc = None
                self._active_run_id = None

        resume_file = RUNS_DATA_DIR / f"{run_id}.resume.json"
        if resume_file.exists():
            try:
                resume_file.unlink()
            except Exception:
                pass

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
            if was_stopped or exit_code < 0:
                final_status = "stopped"
            elif exit_code == 0:
                final_status = "completed"
            else:
                final_status = "failed"
            run_store.apply_event(
                IngestEvent(
                    event_type="run_finish",
                    run_id=run_id,
                    timestamp=now_iso(),
                    payload={"status": final_status, "exit_code": exit_code},
                )
            )


runner_manager = RunnerManager()
