"""Pydantic data models for test runs, hierarchical tree nodes, logs, and ingest events."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

TestStatus = Literal["pending", "running", "passed", "failed", "skipped", "error", "warning"]
RunStatus = Literal["idle", "running", "completed", "failed", "stopped"]
LogStream = Literal["stdout", "stderr", "system"]
LogLevel = Literal["info", "step", "warn", "error", "success"]


class EnvironmentInfo(BaseModel):
    os: str = ""
    hostname: str = ""
    ip: str = ""
    python_version: str = ""
    is_admin: bool = False


class LogLine(BaseModel):
    seq: int
    timestamp: str
    stream: LogStream = "stdout"
    level: LogLevel = "info"
    stage: str | None = None
    text: str
    nodeid: str | None = None


class TestCaseState(BaseModel):
    nodeid: str
    tc_id: str = ""
    id: str
    title: str
    docstring: str = ""
    domain: str
    domain_title: str
    category_id: str
    category_title: str
    subcategory_id: str | None = None
    subcategory_title: str | None = None
    markers: list[str] = Field(default_factory=list)
    status: TestStatus = "pending"
    duration: float | None = None
    started_at: str | None = None
    finished_at: str | None = None
    summary: str = ""
    error_message: str = ""
    logs: list[LogLine] = Field(default_factory=list)


class RunSummary(BaseModel):
    total: int = 0
    completed: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    running: int = 0
    pending: int = 0
    pass_rate: float = 0.0
    duration_sec: float = 0.0


class RunState(BaseModel):
    run_id: str
    title: str
    target: str = "custom"
    status: RunStatus = "running"
    started_at: str
    finished_at: str | None = None
    environment: EnvironmentInfo = Field(default_factory=EnvironmentInfo)
    summary: RunSummary = Field(default_factory=RunSummary)
    cases: list[TestCaseState] = Field(default_factory=list)
    session_logs: list[LogLine] = Field(default_factory=list)
    active_nodeid: str | None = None


class IngestEvent(BaseModel):
    event_type: Literal[
        "run_start",
        "collection_ready",
        "case_start",
        "log",
        "case_finish",
        "run_finish",
    ]
    run_id: str
    timestamp: str
    payload: dict[str, Any] = Field(default_factory=dict)


class IngestBatchRequest(BaseModel):
    events: list[IngestEvent]


class StartRunRequest(BaseModel):
    target: str = "app"
    markers: str | None = None
    keyword: str | None = None
    paths: list[str] = Field(default_factory=list)
    nodeids: list[str] = Field(default_factory=list)
    title: str | None = None
    run_id: str | None = None
    accumulate: bool = True


class DeleteRunsRequest(BaseModel):
    run_ids: list[str] | None = None


class CatalogTargetPreset(BaseModel):
    id: str
    label: str
    domain: str
    markers: str | None = None
    paths: list[str] = Field(default_factory=list)
    description: str = ""
