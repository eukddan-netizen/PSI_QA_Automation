"""Optional structured logger helper for QA tests (backward-compatible with plain print)."""

from __future__ import annotations


def step_log(stage: str, message: str) -> None:
    """
    Prints a standardized bracketed stage log.
    Existing stdout teeing in dashboard/pytest_plugin.py automatically parses
    `>>> [stage] message` into structured dashboard step logs without extra coupling.
    """
    print(f">>> [{stage}] {message}")
