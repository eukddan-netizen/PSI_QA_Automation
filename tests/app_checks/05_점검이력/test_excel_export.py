"""
점검 내역 엑셀 내보내기 및 파일 정합성 검증 테스트 (요구사항 8 / Row 45~47)
- 우측 상단 엑셀 아이콘 클릭 -> '#32770' 저장 다이얼로그에서 바탕화면 저장
- 저장 완료 팝업("점검 내역을 엑셀 파일로 저장했습니다.") 확인
- 저장된 .xlsx 파일을 openpyxl로 열어 파일명, 버전, 사용자 정보, 점검결과/점수 데이터 및 단위 표기('개'/'점'),
  전체 보안점검 항목명/결과/상세설명 정합성 검증
"""

from datetime import datetime
from pathlib import Path
import openpyxl
import pytest

from common.os_utils import require_admin
from pages.client.history_page import HistoryPage, get_user_desktop_dir


def _normalize_ws(text: str) -> str:
    return " ".join((str(text) if text is not None else "").split())


def _expected_excel_filename(inspection_time: str) -> str:
    dt = datetime.strptime(inspection_time.strip(), "%Y-%m-%d %H:%M:%S")
    return f"내PC보안점검_{dt.strftime('%Y%m%d_%H%M%S')}.xlsx"


@pytest.mark.app_check
@pytest.mark.app_history
def test_010_점검이력_엑셀내보내기_정합성(history_test_session, server_history_data):
    """
    [APP-05-02-010] 점검이력 엑셀 내보내기 저장 및 파일명·본문 데이터 정합성 검증
    우측 상단 엑셀 아이콘 클릭 -> 바탕화면 저장 -> 완료 팝업 확인 ->
    저장된 엑셀 파일의 파일명, 사용자정보, 점검결과/점수 데이터와 단위, 전체 항목명/상세설명 정합성 검증
    """
    require_admin(
        "엑셀 저장 다이얼로그(#32770) 제어(Windows UIPI 제약)를 위해 "
        "PowerShell을 '관리자 권한으로 실행(Run as Administrator)'해야 합니다."
    )

    history_page: HistoryPage = history_test_session["history_page"]
    app_version = history_test_session["app_version"]
    expected_safety_score = server_history_data["safety_score"]

    # 1. 최신 점검 상세 내역 화면 진입 및 UI 기준 데이터 수집
    history_page.ensure_latest_detail_view()

    detail_user = history_page.get_detail_user_info()
    detail_summary = history_page.get_detail_summary()

    _, toggle_label = history_page.get_toggle_all_button_state()
    if toggle_label == "전체 열기":
        history_page.click_toggle_all(expected_next_label="전체 닫기")
    detail_items = history_page.get_detail_items()
    assert detail_items, "상세 내역에 비교할 점검 항목이 없습니다."

    expected_filename = _expected_excel_filename(detail_user["inspection_time"])
    desktop_dir = get_user_desktop_dir()
    saved_path: Path | None = None

    try:
        # 2. 우측 상단 엑셀 아이콘 클릭 -> 바탕화면에 저장 -> 완료 팝업 확인
        history_page.click_excel_export_icon()
        save_res = history_page.save_excel_to_desktop(desktop_dir=desktop_dir, timeout=10.0)
        saved_path = save_res["saved_path"]

        popup_msg = history_page.wait_for_excel_save_popup(timeout=8.0)
        print(f"\n>>> [엑셀 저장 팝업] {popup_msg!r}")
        assert "점검 내역을 엑셀 파일로 저장했습니다" in popup_msg, (
            f"엑셀 저장 완료 팝업 문구가 예상과 다릅니다: {popup_msg!r}"
        )

        # 3. 파일명 및 바탕화면 파일 존재 여부 검증
        print(f">>> [엑셀 파일 검증] 경로={saved_path}, 기대파일명={expected_filename}")
        assert save_res["default_filename"] == expected_filename, (
            f"저장 다이얼로그 기본 파일명 불일치: 실제='{save_res['default_filename']}', 기대='{expected_filename}'"
        )
        assert saved_path is not None and saved_path.exists(), (
            f"바탕화면에 엑셀 파일이 저장되지 않았습니다: {saved_path}"
        )
        assert saved_path.name == expected_filename, (
            f"저장된 파일명 불일치: 실제='{saved_path.name}', 기대='{expected_filename}'"
        )

        # 4. openpyxl로 엑셀 내용 파싱 및 정합성 검증
        wb = openpyxl.load_workbook(saved_path, data_only=True)
        try:
            ws = wb.active
            assert ws is not None, "엑셀 워크시트를 열 수 없습니다."

            title_val = str(ws.cell(1, 1).value or "").strip()
            excel_version = str(ws.cell(2, 1).value or "").strip()
            assert "PC보안점검 보고서" in title_val, f"엑셀 1행 보고서 제목 이상: {title_val!r}"
            assert excel_version == detail_user["version"] == app_version, (
                f"엑셀 2행 버전 불일치: 엑셀='{excel_version}', UI상세='{detail_user['version']}', 설정='{app_version}'"
            )

            # 메타데이터 블록(사용자 정보 + 점검 결과 요약) 파싱
            left_meta = {}
            right_meta = {}
            table_header_row = None

            for r in range(3, ws.max_row + 1):
                c1 = ws.cell(r, 1).value
                c2 = ws.cell(r, 2).value
                c3 = ws.cell(r, 3).value
                c4 = ws.cell(r, 4).value
                if [str(x).strip() if x is not None else "" for x in (c1, c2, c3, c4)] == [
                    "번호",
                    "점검 항목",
                    "결과",
                    "상세 설명",
                ]:
                    table_header_row = r
                    break
                if c1 is not None:
                    left_meta[str(c1).strip()] = str(c2).strip() if c2 is not None else ""
                if c3 is not None:
                    right_meta[str(c3).strip()] = str(c4).strip() if c4 is not None else ""

            assert table_header_row is not None, "엑셀에서 점검 항목 테이블 헤더(['번호', '점검 항목', '결과', '상세 설명'])를 찾지 못했습니다."

            print(f">>> [엑셀 사용자정보] {left_meta}")
            print(f">>> [엑셀 요약/점수]  {right_meta}")

            # 4-1. 사용자 정보 검증
            user_checks = [
                ("점검 일시", detail_user.get("inspection_time")),
                ("사용자 IP", detail_user.get("ip")),
                ("사용자명", detail_user.get("username")),
                ("부서명", detail_user.get("department")),
                ("OS 정보", detail_user.get("os")),
                ("바이러스 백신", detail_user.get("antivirus")),
            ]
            for label, expected_val in user_checks:
                assert left_meta.get(label) == expected_val, (
                    f"엑셀 '{label}' 불일치: 엑셀={left_meta.get(label)!r} != UI={expected_val!r}"
                )
            assert left_meta.get("서버 전송 상태") == "전송 완료", (
                f"엑셀 '서버 전송 상태'가 '전송 완료'가 아닙니다: {left_meta.get('서버 전송 상태')!r}"
            )

            # 4-2. 점검결과 및 점수의 데이터와 단위 표기('개', '점') 검증
            total_count = (
                detail_summary["safe_count"]
                + detail_summary["vulnerable_count"]
                + detail_summary["unable_count"]
                + detail_summary["uninspected_count"]
            )
            expected_summary_cells = {
                "전체": f"{total_count}개",
                "미점검": f"{detail_summary['uninspected_count']}개",
                "점검불가": f"{detail_summary['unable_count']}개",
                "취약": f"{detail_summary['vulnerable_count']}개",
                "안전": f"{detail_summary['safe_count']}개",
                "안전 기준 점수": f"{expected_safety_score}점",
                "사용자 점수": f"{detail_summary['score']}점",
            }
            for label, expected_str in expected_summary_cells.items():
                actual_str = right_meta.get(label)
                assert actual_str == expected_str, (
                    f"엑셀 '{label}' 데이터/단위 불일치: 엑셀={actual_str!r} != 기대={expected_str!r}"
                )

            # 4-3. 각 보안점검 항목(번호, 항목명, 결과, 상세 설명) 전수 검증
            excel_rows = {}
            for r in range(table_header_row + 1, ws.max_row + 1):
                no_val = ws.cell(r, 1).value
                if no_val is None:
                    continue
                no_int = int(str(no_val).strip())
                excel_rows[no_int] = {
                    "no": no_int,
                    "title": str(ws.cell(r, 2).value or "").strip(),
                    "status": str(ws.cell(r, 3).value or "").strip(),
                    "description": str(ws.cell(r, 4).value or "").strip(),
                }

            assert len(excel_rows) == len(detail_items), (
                f"엑셀 점검 항목 수({len(excel_rows)}개) != UI 상세 내역 항목 수({len(detail_items)}개)"
            )

            errors = []
            for ui_item in detail_items:
                no = ui_item["no"]
                ex_item = excel_rows.get(no)
                if ex_item is None:
                    errors.append(f"[{no}번] 엑셀 보고서에 항목이 누락되었습니다.")
                    continue
                if ex_item["title"] != ui_item["title"]:
                    errors.append(f"[{no}번] 항목명 불일치: 엑셀='{ex_item['title']}' != UI='{ui_item['title']}'")
                if ex_item["status"] != ui_item["status"]:
                    errors.append(f"[{no}번 {ui_item['title']}] 결과 불일치: 엑셀='{ex_item['status']}' != UI='{ui_item['status']}'")
                if not ex_item["description"]:
                    errors.append(f"[{no}번 {ui_item['title']}] 엑셀 상세 설명이 비어 있습니다.")
                elif _normalize_ws(ex_item["description"]) != _normalize_ws(ui_item["description"]):
                    errors.append(
                        f"[{no}번 {ui_item['title']}] 상세 설명 불일치:\n"
                        f"  엑셀={_normalize_ws(ex_item['description'])}\n"
                        f"  UI  ={_normalize_ws(ui_item['description'])}"
                    )

            assert not errors, "\n".join(errors)
            print(f">>> [엑셀 보고서 검증 완료] 파일명/사용자정보/요약단위/{len(excel_rows)}개 전 항목명·결과·상세설명 100% 일치!")
        finally:
            wb.close()
    finally:
        if saved_path is not None and saved_path.exists():
            try:
                saved_path.unlink()
                print(f">>> [정리] 테스트 생성 엑셀 파일 삭제 완료: {saved_path}")
            except Exception as exc:
                print(f">>> [정리 경고] 엑셀 파일 삭제 실패 ({saved_path}): {exc}")
