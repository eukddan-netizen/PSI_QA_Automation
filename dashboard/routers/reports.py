"""Report export endpoints (.xlsx and .docx) using point-in-time run snapshots."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from dashboard.reports.excel_builder import build_excel_report
from dashboard.reports.word_builder import build_word_report
from dashboard.store import run_store

router = APIRouter(tags=["reports"])


@router.get("/api/runs/{run_id}/report")
def export_report(
    run_id: str,
    format: str = Query(..., pattern="^(xlsx|docx)$"),
):
    snap = run_store.get_run_snapshot(run_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="보고서를 생성할 실행 이력을 찾을 수 없습니다.")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if format == "xlsx":
        content = build_excel_report(snap)
        filename = f"QA_점검결과보고서_{ts}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = build_word_report(snap)
        filename = f"QA_점검결과보고서_{ts}.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    encoded_name = quote(filename)
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"qa_report_{ts}.{format}\"; filename*=UTF-8''{encoded_name}",
            "Cache-Control": "no-store",
        },
    )
