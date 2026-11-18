"""Catalog and test-collection endpoints."""

from __future__ import annotations

from fastapi import APIRouter

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
