"""FastAPI application entry point for the local QA Automation Dashboard."""

from __future__ import annotations

import argparse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from dashboard.config import DEFAULT_HOST, DEFAULT_PORT, STATIC_DIR
from dashboard.routers import catalog, reports, runs

app = FastAPI(
    title="PSI QA Automation Dashboard",
    version="1.0.0",
    description="로컬 전용 QA 자동화 실시간 로그 대시보드 및 정부 표준 보고서 추출 서버",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog.router)
app.include_router(runs.router)
app.include_router(reports.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(STATIC_DIR / "index.html"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the PSI QA Automation Dashboard server")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run(
        "dashboard.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        timeout_graceful_shutdown=1,
    )


if __name__ == "__main__":
    main()
