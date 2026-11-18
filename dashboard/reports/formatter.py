"""Korean public-sector / government report style formatter (개조식 & 기호 위계)."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from dashboard.models import RunState, TestCaseState


STATUS_LABELS: dict[str, str] = {
    "passed": "정상",
    "failed": "오류",
    "error": "오류",
    "skipped": "제외",
    "running": "진행중",
    "pending": "대기",
    "warning": "경고",
}


@dataclass
class CategoryRollup:
    domain_title: str
    category_title: str
    total: int
    completed: int
    passed: int
    failed: int
    skipped: int
    pending: int


@dataclass
class PreparedReportData:
    doc_title: str
    snapshot_time: str
    is_partial: bool
    run_status_label: str
    period_text: str
    env_text: str
    total: int
    completed: int
    passed: int
    failed: int
    skipped: int
    remaining: int
    pass_rate: float
    total_duration: float
    opinion_bullets: list[str]
    footnote: str
    category_rollups: list[CategoryRollup]
    completed_cases: list[TestCaseState]
    all_cases: list[TestCaseState]


def format_duration_ko(seconds: float) -> str:
    """Formats duration as 'xx.xx초' under 1 minute, or 'xx분 xx초' (with hours if >= 1h)."""
    if seconds < 0:
        return "0.00초"
    if seconds < 60:
        return f"{seconds:.2f}초"
    total_sec = round(seconds)
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"{hours}시간 {minutes:02d}분 {secs:02d}초"
    return f"{minutes}분 {secs:02d}초"


def to_gaejosik(text: str, default_end: str = "함") -> str:
    """Normalizes a Korean sentence into concise government bullet phrasing (~함/~임/~됨)."""
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return ""

    # Trim trailing punctuation
    cleaned = cleaned.rstrip(".")

    # Common declarative/polite endings → 개조식 명사형
    replacements = [
        (r"일치하지 않습니다$", "불일치 확인됨"),
        (r"일치하지 않음$", "불일치 확인됨"),
        (r"다릅니다$", "상이함"),
        (r"없습니다$", "미존재 확인됨"),
        (r"있습니다$", "존재 확인됨"),
        (r"실패했습니다$", "실패함"),
        (r"완료했습니다$", "완료함"),
        (r"완료되었습니다$", "완료됨"),
        (r"변경되었습니다$", "변경됨"),
        (r"변경되지 않았습니다$", "미변경 확인됨"),
        (r"출력되었습니다$", "출력됨"),
        (r"읽을 수 없습니다$", "조회 불가함"),
        (r"확인되었습니다$", "확인됨"),
        (r"확인했습니다$", "확인함"),
        (r"필요합니다$", "필요함"),
        (r"해야 합니다$", "요구됨"),
        (r"아닙니다$", "아님"),
        (r"합니다$", "함"),
        (r"됩니다$", "됨"),
        (r"입니다$", "임"),
        (r"습니다$", "음"),
    ]
    for pattern, repl in replacements:
        if re.search(pattern, cleaned):
            return re.sub(pattern, repl, cleaned)

    if cleaned.endswith(("함", "임", "됨", "음", "됨)", "함)", "임)")):
        return cleaned
    return f"{cleaned} ({default_end})" if len(cleaned) < 60 else cleaned


def format_case_detail_gaejosik(case: TestCaseState) -> str:
    """Formats a single test case outcome into Korean government 개조식 bullet content."""
    if case.status == "passed":
        dur = f"{case.duration:.2f}초" if case.duration is not None else "-"
        base = _clean_docstring_subject(case.docstring) or case.title
        return f"{base}에 대한 정상 동작 및 정합성 검증 완료함 (소요시간 {dur})"

    if case.status in ("failed", "error"):
        err = (case.error_message or "").splitlines()[0].strip() if case.error_message else ""
        if err:
            return f"점검 기준 불충족 확인됨 — {to_gaejosik(err, default_end='오류')}"
        return "점검 수행 중 예외 또는 기준 불일치 발생함"

    if case.status == "skipped":
        reason = (case.error_message or "").splitlines()[0].strip() if case.error_message else "사전 실행 조건 미충족"
        return f"점검 대상 제외됨 — {to_gaejosik(reason, default_end='제외')}"

    if case.status == "running":
        return "현재 점검 수행 중임"

    return "점검 대기 상태임"


def format_case_note(case: TestCaseState) -> str:
    if case.status in ("failed", "error"):
        return "조치 및 재검증 필요"
    if case.status == "skipped":
        return "실행 조건 확인"
    if case.subcategory_title:
        return case.subcategory_title
    return "-"


def _clean_docstring_subject(docstring: str) -> str:
    if not docstring:
        return ""
    for line in docstring.splitlines():
        s = line.strip()
        if not s or s.startswith("-") or s.startswith("="):
            continue
        s = re.sub(r"^\[[^\]]+\]\s*", "", s)
        if len(s) > 65:
            s = s[:62].rstrip() + "..."
        return s
    return ""


def prepare_report_data(run: RunState) -> PreparedReportData:
    snapshot_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    completed_cases = [c for c in run.cases if c.status in ("passed", "failed", "error", "skipped")]
    passed = sum(1 for c in completed_cases if c.status == "passed")
    failed = sum(1 for c in completed_cases if c.status in ("failed", "error"))
    skipped = sum(1 for c in completed_cases if c.status == "skipped")
    total = len(run.cases)
    completed = len(completed_cases)
    remaining = max(0, total - completed)
    is_partial = run.status == "running" or remaining > 0

    denom = passed + failed
    pass_rate = round((passed / denom) * 100.0, 1) if denom > 0 else (100.0 if passed > 0 else 0.0)
    total_duration = round(sum(c.duration or 0.0 for c in completed_cases), 2)

    run_status_map = {
        "running": "진행중 (중간 스냅샷)",
        "completed": "전체 완료",
        "failed": "완료 (오류 포함)",
        "stopped": "중단됨",
        "idle": "대기",
    }
    run_status_label = run_status_map.get(run.status, run.status)

    end_ref = run.finished_at or snapshot_dt
    period_text = f"{run.started_at[:19]} ~ {end_ref[:19]}"

    env = run.environment
    env_parts = [p for p in [env.os, env.hostname, env.ip] if p]
    admin_label = "관리자 권한" if env.is_admin else "일반 권한"
    env_text = " / ".join(env_parts) + f" ({admin_label})" if env_parts else admin_label

    # Category rollups preserving insertion order
    grouped: dict[tuple[str, str], list[TestCaseState]] = defaultdict(list)
    for c in run.cases:
        grouped[(c.domain_title, c.category_title)].append(c)

    rollups: list[CategoryRollup] = []
    for (dom_t, cat_t), items in grouped.items():
        c_pass = sum(1 for i in items if i.status == "passed")
        c_fail = sum(1 for i in items if i.status in ("failed", "error"))
        c_skip = sum(1 for i in items if i.status == "skipped")
        c_comp = c_pass + c_fail + c_skip
        rollups.append(
            CategoryRollup(
                domain_title=dom_t,
                category_title=cat_t,
                total=len(items),
                completed=c_comp,
                passed=c_pass,
                failed=c_fail,
                skipped=c_skip,
                pending=len(items) - c_comp,
            )
        )

    opinions: list[str] = [
        f"전체 대상 {total}건 중 {completed}건 점검 완료됨 (정상 {passed}건, 오류 {failed}건, 제외 {skipped}건, 정상률 {pass_rate:.1f}%)",
    ]
    if failed == 0 and completed > 0:
        opinions.append("현재까지 완료된 모든 항목이 기준에 부합하여 정상 판정됨")
    elif failed > 0:
        fail_ids = [c.tc_id or c.id for c in completed_cases if c.status in ("failed", "error")]
        fail_names = ", ".join(fail_ids[:5])
        if len(fail_ids) > 5:
            fail_names += f" 외 {len(fail_ids) - 5}건"
        opinions.append(f"오류 발생 {failed}건에 대해 원인 분석 및 조치 후 재점검 필요함 (주요 항목: {fail_names})")
    if is_partial:
        opinions.append(f"보고서 추출 시점 기준 잔여 {remaining}건은 점검 진행중 또는 대기 상태임")

    footnote = (
        f"※ 본 보고서는 {snapshot_dt} 시점까지 완료된 점검 결과({completed}/{total}건)를 기준으로 자동 생성되었음."
    )

    return PreparedReportData(
        doc_title="보안 에이전트 QA 자동화 점검 결과 보고서",
        snapshot_time=snapshot_dt,
        is_partial=is_partial,
        run_status_label=run_status_label,
        period_text=period_text,
        env_text=env_text,
        total=total,
        completed=completed,
        passed=passed,
        failed=failed,
        skipped=skipped,
        remaining=remaining,
        pass_rate=pass_rate,
        total_duration=total_duration,
        opinion_bullets=opinions,
        footnote=footnote,
        category_rollups=rollups,
        completed_cases=completed_cases,
        all_cases=run.cases,
    )
