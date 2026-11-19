"""Run lifecycle, event ingestion, and SSE real-time streaming endpoints."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import StreamingResponse

from dashboard.models import DeleteRunsRequest, IngestBatchRequest, StartRunRequest
from dashboard.runner_manager import runner_manager
from dashboard.store import run_store

router = APIRouter(tags=["runs"])


@router.post("/api/ingest/events")
def ingest_events(batch: IngestBatchRequest):
    for ev in batch.events:
        run_store.apply_event(ev)
    return {"accepted": len(batch.events)}


@router.get("/api/runs")
def list_runs():
    return {
        "runs": run_store.list_runs(),
        "runner": runner_manager.get_status(),
    }


@router.delete("/api/runs")
def delete_runs(req: DeleteRunsRequest | None = Body(default=None)):
    runner_status = runner_manager.get_status()
    active_run_id = runner_status.get("active_run_id")

    if req is not None and req.run_ids is not None:
        if runner_status.get("is_running") and active_run_id in req.run_ids:
            raise HTTPException(status_code=409, detail="현재 실행 중인 테스트 이력은 삭제할 수 없습니다. 먼저 중단해 주세요.")
        deleted_ids = run_store.delete_runs(req.run_ids)
        return {
            "deleted_ids": deleted_ids,
            "cleared": len(deleted_ids),
            "runs": run_store.list_runs(),
            "runner": runner_manager.get_status(),
        }

    if runner_manager.is_running():
        raise HTTPException(status_code=409, detail="테스트 실행 중에는 초기화할 수 없습니다. 먼저 중단해 주세요.")
    deleted_ids = run_store.delete_runs(None)
    return {
        "deleted_ids": deleted_ids,
        "cleared": len(deleted_ids),
        "runs": run_store.list_runs(),
        "runner": runner_manager.get_status(),
    }


@router.get("/api/runs/latest")
def get_latest_run():
    latest = run_store.get_latest_run()
    return {
        "run": latest.model_dump() if latest else None,
        "runner": runner_manager.get_status(),
    }


@router.get("/api/runs/{run_id}")
def get_run(run_id: str):
    snap = run_store.get_run_snapshot(run_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="실행 이력을 찾을 수 없습니다.")
    return {"run": snap.model_dump(), "runner": runner_manager.get_status()}


@router.post("/api/runs")
def start_run(req: StartRunRequest):
    try:
        result = runner_manager.start_run(req)
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/resume")
def resume_run(run_id: str):
    try:
        return runner_manager.resume_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/retry-failed")
def retry_failed_run(run_id: str):
    try:
        return runner_manager.retry_failed_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/stop")
def stop_run(run_id: str):
    return runner_manager.stop_run(run_id)


async def _sse_generator(request: Request, channel_id: str, initial_run_id: str | None) -> AsyncIterator[str]:
    loop = asyncio.get_running_loop()
    q = run_store.broadcaster.subscribe(channel_id, loop)
    try:
        if initial_run_id:
            snap = run_store.get_run_snapshot(initial_run_id)
            if snap is not None:
                data = json.dumps(snap.model_dump(), ensure_ascii=False)
                yield f"event: snapshot\ndata: {data}\n\n"
        else:
            latest = run_store.get_latest_run()
            if latest is not None:
                data = json.dumps(latest.model_dump(), ensure_ascii=False)
                yield f"event: snapshot\ndata: {data}\n\n"

        while True:
            if await request.is_disconnected():
                break
            try:
                msg = await asyncio.wait_for(q.get(), timeout=15.0)
                data = json.dumps(msg["data"], ensure_ascii=False)
                yield f"event: {msg['event']}\ndata: {data}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        run_store.broadcaster.unsubscribe(channel_id, loop, q)


@router.get("/api/stream")
async def stream_all_runs(request: Request):
    """Global SSE stream: delivers latest snapshot + live events for any new/active CLI or UI run."""
    return StreamingResponse(
        _sse_generator(request, channel_id="__all__", initial_run_id=None),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/runs/{run_id}/stream")
async def stream_single_run(run_id: str, request: Request):
    return StreamingResponse(
        _sse_generator(request, channel_id=run_id, initial_run_id=run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
