"""Catalog and test-collection endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from dashboard.case_collector import catalog_case_cache
from dashboard.catalog_loader import catalog_registry
from dashboard.runner_manager import runner_manager

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("")
def get_catalog():
    catalog_registry.reload()
    return {
        **catalog_registry.get_catalog_overview(),
        "runner": runner_manager.get_status(),
    }


@router.get("/cases")
def get_catalog_cases(refresh: bool = Query(default=False)):
    try:
        cases = catalog_case_cache.get_cases(refresh=refresh)
        return {
            "cases": cases,
            "count": len(cases),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
