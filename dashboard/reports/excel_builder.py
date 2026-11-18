"""Korean government report Excel (.xlsx) generator using openpyxl."""

from __future__ import annotations

import io
import math
import unicodedata
from openpyxl import Workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from dashboard.models import RunState
from dashboard.reports.formatter import (
    STATUS_LABELS,
    format_case_detail_gaejosik,
    format_case_note,
    format_duration_ko,
    prepare_report_data,
)


def _display_width(text: object) -> float:
    """Estimates Excel display width accounting for East Asian wide characters."""
    if text is None:
        return 0.0
    max_line = 0.0
    for line in str(text).splitlines() or [""]:
        w = 0.0
        for ch in line:
            if unicodedata.east_asian_width(ch) in ("W", "F"):
                w += 2.15
            else:
                w += 1.15
        if w > max_line:
            max_line = w
    return max_line


def _auto_fit_columns(ws, min_widths: dict[int, float], max_widths: dict[int, float] | None = None) -> None:
    max_widths = max_widths or {}
    col_widths: dict[int, float] = dict(min_widths)
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell, MergedCell) or cell.value is None:
                continue
            col_idx = cell.column
            # Skip title rows (row 1) so wide headers don't distort column A
            if cell.row <= 2:
                continue
            w = _display_width(cell.value) + 4.0
            if w > col_widths.get(col_idx, 0.0):
                col_widths[col_idx] = w

    for col_idx, width in col_widths.items():
        cap = max_widths.get(col_idx, 60.0)
        ws.column_dimensions[get_column_letter(col_idx)].width = round(min(width, cap), 1)


def build_excel_report(run: RunState) -> bytes:
    data = prepare_report_data(run)
    wb = Workbook()

    # Palette (clean monochrome + subtle government blue-gray header)
    header_fill = PatternFill("solid", fgColor="1E293B")
    sub_header_fill = PatternFill("solid", fgColor="E2E8F0")
    label_fill = PatternFill("solid", fgColor="F1F5F9")
    pass_fill = PatternFill("solid", fgColor="ECFDF5")
    fail_fill = PatternFill("solid", fgColor="FEF2F2")
    skip_fill = PatternFill("solid", fgColor="F8FAFC")

    thin = Side(border_style="thin", color="94A3B8")
    med = Side(border_style="medium", color="334155")
    grid_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    title_bottom = Border(bottom=med)

    font_title = Font(name="맑은 고딕", size=15, bold=True, color="0F172A")
    font_h2 = Font(name="맑은 고딕", size=11, bold=True, color="0F172A")
    font_th = Font(name="맑은 고딕", size=10, bold=True, color="FFFFFF")
    font_th_sub = Font(name="맑은 고딕", size=10, bold=True, color="1E293B")
    font_body = Font(name="맑은 고딕", size=9.5, color="0F172A")
    font_bold = Font(name="맑은 고딕", size=9.5, bold=True, color="0F172A")
    font_note = Font(name="맑은 고딕", size=9, italic=False, color="475569")
    font_pass = Font(name="맑은 고딕", size=9.5, bold=True, color="047857")
    font_fail = Font(name="맑은 고딕", size=9.5, bold=True, color="B91C1C")
    font_skip = Font(name="맑은 고딕", size=9.5, bold=True, color="64748B")

    # ------------------------------------------------------------------
    # Sheet 1: 종합 요약
    # ------------------------------------------------------------------
    ws1 = wb.active
    ws1.title = "종합 요약"
    ws1.views.sheetView[0].showGridLines = True

    ws1.merge_cells("A1:G1")
    ws1["A1"] = f"□ {data.doc_title}"
    ws1["A1"].font = font_title
    ws1["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws1.row_dimensions[1].height = 34
    for col_idx in range(1, 8):
        ws1.cell(row=1, column=col_idx).border = title_bottom

    # Section 1: 점검 개요
    ws1["A3"] = "○ 1. 점검 개요"
    ws1["A3"].font = font_h2
    ws1.row_dimensions[3].height = 22

    overview_rows = [
        ("점검 대상", run.title, "실행 상태", data.run_status_label),
        ("점검 일시", data.period_text, "보고서 기준 시각", data.snapshot_time),
        ("실행 환경", data.env_text, "누적 소요 시간", format_duration_ko(data.total_duration)),
    ]
    for offset, (k1, v1, k2, v2) in enumerate(overview_rows, start=4):
        ws1.row_dimensions[offset].height = 24
        ws1.cell(offset, 1, k1).font = font_th_sub
        ws1.cell(offset, 1).fill = label_fill
        ws1.cell(offset, 1).alignment = Alignment(horizontal="center", vertical="center")

        ws1.merge_cells(start_row=offset, start_column=2, end_row=offset, end_column=4)
        ws1.cell(offset, 2, v1).font = font_body
        ws1.cell(offset, 2).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        ws1.cell(offset, 5, k2).font = font_th_sub
        ws1.cell(offset, 5).fill = label_fill
        ws1.cell(offset, 5).alignment = Alignment(horizontal="center", vertical="center")

        ws1.merge_cells(start_row=offset, start_column=6, end_row=offset, end_column=7)
        ws1.cell(offset, 6, v2).font = font_body
        ws1.cell(offset, 6).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        for c in range(1, 8):
            ws1.cell(offset, c).border = grid_border

    # Section 2: 점검 결과 요약
    ws1["A8"] = "○ 2. 점검 결과 요약"
    ws1["A8"].font = font_h2
    ws1.row_dimensions[8].height = 22

    kpi_headers = ["전체 대상(건)", "점검 완료(건)", "정상(건)", "오류(건)", "제외(건)", "미완료(건)", "정상률(%)"]
    kpi_values = [
        data.total,
        data.completed,
        data.passed,
        data.failed,
        data.skipped,
        data.remaining,
        f"{data.pass_rate:.1f}%",
    ]
    ws1.row_dimensions[9].height = 24
    ws1.row_dimensions[10].height = 26
    for idx, (h, val) in enumerate(zip(kpi_headers, kpi_values), start=1):
        hc = ws1.cell(9, idx, h)
        hc.font = font_th
        hc.fill = header_fill
        hc.alignment = Alignment(horizontal="center", vertical="center")
        hc.border = grid_border

        vc = ws1.cell(10, idx, val)
        vc.font = font_fail if idx == 4 and data.failed > 0 else (font_pass if idx == 3 else font_bold)
        vc.alignment = Alignment(horizontal="center", vertical="center")
        vc.border = grid_border

    # Section 3: 대분류·중분류별 점검 현황
    ws1["A12"] = "○ 3. 중분류별 점검 현황"
    ws1["A12"].font = font_h2
    ws1.row_dimensions[12].height = 22

    cat_headers = ["대분류", "중분류", "대상(건)", "완료(건)", "정상(건)", "오류(건)", "제외/대기(건)"]
    ws1.row_dimensions[13].height = 24
    for idx, h in enumerate(cat_headers, start=1):
        c = ws1.cell(13, idx, h)
        c.font = font_th_sub
        c.fill = sub_header_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = grid_border

    cur_row = 14
    for rollup in data.category_rollups:
        ws1.row_dimensions[cur_row].height = 22
        vals = [
            rollup.domain_title,
            rollup.category_title,
            rollup.total,
            rollup.completed,
            rollup.passed,
            rollup.failed,
            f"{rollup.skipped} / {rollup.pending}",
        ]
        for idx, val in enumerate(vals, start=1):
            cell = ws1.cell(cur_row, idx, val)
            cell.font = font_fail if idx == 6 and rollup.failed > 0 else font_body
            cell.alignment = Alignment(horizontal="left" if idx <= 2 else "center", vertical="center")
            cell.border = grid_border
        cur_row += 1

    # Section 4: 종합 의견
    cur_row += 1
    ws1.cell(cur_row, 1, "○ 4. 종합 의견").font = font_h2
    ws1.row_dimensions[cur_row].height = 22
    cur_row += 1

    for bullet in data.opinion_bullets:
        ws1.merge_cells(start_row=cur_row, start_column=1, end_row=cur_row, end_column=7)
        c = ws1.cell(cur_row, 1, f"  ― {bullet}")
        c.font = font_body
        c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws1.row_dimensions[cur_row].height = 22
        cur_row += 1

    ws1.merge_cells(start_row=cur_row, start_column=1, end_row=cur_row, end_column=7)
    fn = ws1.cell(cur_row, 1, data.footnote)
    fn.font = font_note
    fn.alignment = Alignment(horizontal="left", vertical="center")
    ws1.row_dimensions[cur_row].height = 20

    _auto_fit_columns(
        ws1,
        min_widths={1: 34, 2: 34, 3: 14, 4: 14, 5: 16, 6: 14, 7: 16},
        max_widths={1: 42, 2: 44, 3: 18, 4: 18, 5: 20, 6: 18, 7: 20},
    )

    # ------------------------------------------------------------------
    # Sheet 2: 세부 점검 결과
    # ------------------------------------------------------------------
    ws2 = wb.create_sheet(title="세부 점검 결과")
    ws2.views.sheetView[0].showGridLines = True

    ws2.merge_cells("A1:I1")
    ws2["A1"] = f"□ 항목별 세부 점검 결과 ({data.snapshot_time} 기준)"
    ws2["A1"].font = font_title
    ws2["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws2.row_dimensions[1].height = 32
    for col_idx in range(1, 10):
        ws2.cell(row=1, column=col_idx).border = title_bottom

    detail_headers = [
        "연번",
        "TC ID",
        "대분류",
        "중분류",
        "테스트 항목",
        "판정",
        "소요시간(초)",
        "세부 점검 내용 (개조식)",
        "비고",
    ]
    ws2.row_dimensions[3].height = 25
    for idx, h in enumerate(detail_headers, start=1):
        c = ws2.cell(3, idx, h)
        c.font = font_th
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = grid_border

    target_cases = data.completed_cases if data.completed_cases else data.all_cases
    for seq_idx, case in enumerate(target_cases, start=1):
        r = seq_idx + 3
        status_kr = STATUS_LABELS.get(case.status, case.status)
        detail_text = f"― {format_case_detail_gaejosik(case)}"
        note_text = format_case_note(case)
        tc_code = case.tc_id or case.id
        dur_val = round(case.duration, 2) if case.duration is not None else "-"

        row_vals = [
            seq_idx,
            tc_code,
            case.domain_title.split(" ")[0],
            case.category_title,
            case.title,
            status_kr,
            dur_val,
            detail_text,
            note_text,
        ]
        for col_idx, val in enumerate(row_vals, start=1):
            cell = ws2.cell(r, col_idx, val)
            cell.border = grid_border
            cell.font = font_body
            cell.alignment = Alignment(
                horizontal="center" if col_idx in (1, 2, 6, 7) else "left",
                vertical="center",
                wrap_text=True,
            )

            if col_idx == 6:
                if case.status == "passed":
                    cell.font = font_pass
                    cell.fill = pass_fill
                elif case.status in ("failed", "error"):
                    cell.font = font_fail
                    cell.fill = fail_fill
                else:
                    cell.font = font_skip
                    cell.fill = skip_fill
            elif case.status in ("failed", "error"):
                cell.fill = fail_fill

        line_count = max(
            math.ceil(len(case.title) / 28),
            math.ceil(len(detail_text) / 38),
            1,
        )
        ws2.row_dimensions[r].height = max(24, min(120, line_count * 16 + 8))

    _auto_fit_columns(
        ws2,
        min_widths={1: 7, 2: 18, 3: 18, 4: 26, 5: 36, 6: 10, 7: 13, 8: 48, 9: 22},
        max_widths={1: 9, 2: 24, 3: 24, 4: 34, 5: 46, 6: 12, 7: 15, 8: 60, 9: 30},
    )

    for ws in (ws1, ws2):
        ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
