"""Korean government standard report Word (.docx) generator using python-docx."""

from __future__ import annotations

import io
from collections import defaultdict
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Mm, Pt, RGBColor

from dashboard.models import RunState, TestCaseState
from dashboard.reports.formatter import (
    STATUS_LABELS,
    format_case_detail_gaejosik,
    format_case_note,
    format_duration_ko,
    prepare_report_data,
)


def _set_cell_bg(cell, hex_color: str) -> None:
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def _set_cell_margins(cell, top=80, bottom=80, left=110, right=110) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for side, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def _set_table_borders(table, color="94A3B8") -> None:
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f"""
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="8" w:space="0" w:color="334155"/>
            <w:bottom w:val="single" w:sz="8" w:space="0" w:color="334155"/>
            <w:left w:val="single" w:sz="4" w:space="0" w:color="{color}"/>
            <w:right w:val="single" w:sz="4" w:space="0" w:color="{color}"/>
            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>
            <w:insideV w:val="single" w:sz="4" w:space="0" w:color="{color}"/>
        </w:tblBorders>
        """
    )
    tblPr.append(borders)


def _set_run_font(run, size_pt: float, bold: bool = False, color: RGBColor | None = None) -> None:
    run.font.name = "맑은 고딕"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")
    run.font.size = Pt(size_pt)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def _add_page_number_footer(section) -> None:
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run("- ")
    _set_run_font(r1, 9, color=RGBColor(0x64, 0x74, 0x8B))

    fld_simple = OxmlElement("w:fldSimple")
    fld_simple.set(qn("w:instr"), "PAGE")
    p._p.append(fld_simple)

    r2 = p.add_run(" -")
    _set_run_font(r2, 9, color=RGBColor(0x64, 0x74, 0x8B))


def build_word_report(run: RunState) -> bytes:
    data = prepare_report_data(run)
    doc = Document()

    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(20)
    section.left_margin = Mm(18)
    section.right_margin = Mm(18)

    header_p = section.header.paragraphs[0]
    header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = header_p.add_run(f"QA 자동화 점검 결과 보고 | {data.snapshot_time}")
    _set_run_font(hr, 8.5, color=RGBColor(0x64, 0x74, 0x8B))
    _add_page_number_footer(section)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "맑은 고딕"
    normal_style._element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")
    normal_style.font.size = Pt(10)

    # □ 대제목
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(10)
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="16" w:space="6" w:color="1E293B"/></w:pBdr>'
    )
    title_p._p.get_or_add_pPr().append(pBdr)
    tr = title_p.add_run(f"□ {data.doc_title}")
    _set_run_font(tr, 15, bold=True, color=RGBColor(0x0F, 0x17, 0x2A))

    # ○ 1. 점검 개요
    h1 = doc.add_paragraph()
    h1.paragraph_format.space_before = Pt(6)
    h1.paragraph_format.space_after = Pt(4)
    _set_run_font(h1.add_run("○ 1. 점검 개요"), 11.5, bold=True, color=RGBColor(0x0F, 0x17, 0x2A))

    overview_tbl = doc.add_table(rows=3, cols=4)
    overview_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(overview_tbl)
    overview_pairs = [
        ("점검 대상", run.title, "실행 상태", data.run_status_label),
        ("점검 일시", data.period_text, "보고서 기준 시각", data.snapshot_time),
        ("실행 환경", data.env_text, "누적 소요 시간", format_duration_ko(data.total_duration)),
    ]
    col_w = [Mm(30), Mm(62), Mm(32), Mm(50)]
    for r_idx, (k1, v1, k2, v2) in enumerate(overview_pairs):
        row = overview_tbl.rows[r_idx]
        for c_idx, (txt, is_key) in enumerate(((k1, True), (v1, False), (k2, True), (v2, False))):
            cell = row.cells[c_idx]
            cell.width = col_w[c_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            _set_cell_margins(cell)
            if is_key:
                _set_cell_bg(cell, "F1F5F9")
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if is_key else WD_ALIGN_PARAGRAPH.LEFT
            _set_run_font(p.add_run(txt), 9.5, bold=is_key, color=RGBColor(0x0F, 0x17, 0x2A))

    # ○ 2. 점검 결과 요약
    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(12)
    h2.paragraph_format.space_after = Pt(4)
    _set_run_font(h2.add_run("○ 2. 점검 결과 요약"), 11.5, bold=True, color=RGBColor(0x0F, 0x17, 0x2A))

    kpi_tbl = doc.add_table(rows=2, cols=7)
    kpi_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(kpi_tbl)
    kpi_headers = ["전체 대상", "점검 완료", "정상", "오류", "제외", "미완료", "정상률"]
    kpi_vals = [
        f"{data.total}건",
        f"{data.completed}건",
        f"{data.passed}건",
        f"{data.failed}건",
        f"{data.skipped}건",
        f"{data.remaining}건",
        f"{data.pass_rate:.1f}%",
    ]
    for c_idx, (kh, kv) in enumerate(zip(kpi_headers, kpi_vals)):
        hc = kpi_tbl.rows[0].cells[c_idx]
        _set_cell_bg(hc, "1E293B")
        _set_cell_margins(hc, top=70, bottom=70, left=60, right=60)
        hp = hc.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        hp.paragraph_format.space_after = Pt(0)
        _set_run_font(hp.add_run(kh), 9.5, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))

        vc = kpi_tbl.rows[1].cells[c_idx]
        _set_cell_margins(vc, top=80, bottom=80, left=60, right=60)
        vp = vc.paragraphs[0]
        vp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        vp.paragraph_format.space_after = Pt(0)
        val_color = RGBColor(0x0F, 0x17, 0x2A)
        if c_idx == 2:
            val_color = RGBColor(0x04, 0x78, 0x57)
        elif c_idx == 3 and data.failed > 0:
            val_color = RGBColor(0xB9, 0x1C, 0x1C)
        _set_run_font(vp.add_run(kv), 10, bold=True, color=val_color)

    for bullet in data.opinion_bullets:
        bp = doc.add_paragraph()
        bp.paragraph_format.left_indent = Mm(4)
        bp.paragraph_format.first_line_indent = Mm(-4)
        bp.paragraph_format.space_before = Pt(3)
        bp.paragraph_format.space_after = Pt(2)
        _set_run_font(bp.add_run(f"― {bullet}"), 9.5, color=RGBColor(0x1E, 0x29, 0x3B))

    # ○ 3. 항목별 상세 점검 결과표
    h3 = doc.add_paragraph()
    h3.paragraph_format.space_before = Pt(12)
    h3.paragraph_format.space_after = Pt(4)
    _set_run_font(h3.add_run("○ 3. 항목별 상세 점검 결과"), 11.5, bold=True, color=RGBColor(0x0F, 0x17, 0x2A))

    target_cases = data.completed_cases if data.completed_cases else data.all_cases
    grouped: dict[str, list[TestCaseState]] = defaultdict(list)
    for c in target_cases:
        grouped[f"{c.domain_title.split(' ')[0]} > {c.category_title}"].append(c)

    for cat_label, items in grouped.items():
        sub_p = doc.add_paragraph()
        sub_p.paragraph_format.left_indent = Mm(2)
        sub_p.paragraph_format.space_before = Pt(6)
        sub_p.paragraph_format.space_after = Pt(3)
        _set_run_font(sub_p.add_run(f"― [{cat_label}] ({len(items)}건)"), 10, bold=True, color=RGBColor(0x1E, 0x29, 0x3B))

        det_tbl = doc.add_table(rows=len(items) + 1, cols=5)
        det_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(det_tbl)
        d_headers = ["TC ID", "테스트 항목", "판정", "세부 점검 내용 (개조식)", "비고"]
        d_widths = [Mm(26), Mm(44), Mm(14), Mm(66), Mm(24)]

        for c_idx, dh in enumerate(d_headers):
            hc = det_tbl.rows[0].cells[c_idx]
            hc.width = d_widths[c_idx]
            _set_cell_bg(hc, "E2E8F0")
            _set_cell_margins(hc, top=60, bottom=60, left=70, right=70)
            hp = hc.paragraphs[0]
            hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            hp.paragraph_format.space_after = Pt(0)
            _set_run_font(hp.add_run(dh), 9, bold=True, color=RGBColor(0x0F, 0x17, 0x2A))

        for idx, case in enumerate(items, start=1):
            row = det_tbl.rows[idx]
            status_kr = STATUS_LABELS.get(case.status, case.status)
            vals = [
                case.tc_id or str(idx),
                case.title,
                status_kr,
                f"― {format_case_detail_gaejosik(case)}",
                format_case_note(case),
            ]
            for c_idx, val in enumerate(vals):
                cell = row.cells[c_idx]
                cell.width = d_widths[c_idx]
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                _set_cell_margins(cell, top=60, bottom=60, left=70, right=70)
                if case.status in ("failed", "error"):
                    _set_cell_bg(cell, "FEF2F2")
                elif c_idx == 2 and case.status == "passed":
                    _set_cell_bg(cell, "ECFDF5")

                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx in (0, 2) else WD_ALIGN_PARAGRAPH.LEFT
                txt_color = RGBColor(0x0F, 0x17, 0x2A)
                is_bold = False
                if c_idx == 2:
                    is_bold = True
                    if case.status == "passed":
                        txt_color = RGBColor(0x04, 0x78, 0x57)
                    elif case.status in ("failed", "error"):
                        txt_color = RGBColor(0xB9, 0x1C, 0x1C)
                    else:
                        txt_color = RGBColor(0x64, 0x74, 0x8B)
                _set_run_font(p.add_run(val), 8.8, bold=is_bold, color=txt_color)

    # ※ 참고/비고
    note_p = doc.add_paragraph()
    note_p.paragraph_format.space_before = Pt(10)
    _set_run_font(note_p.add_run(data.footnote), 9, color=RGBColor(0x47, 0x55, 0x69))

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
