"""
보안점검 프로그램 '점검이력' 탭 페이지 Object
- 점검이력 목록 화면: 상단 최근점검일시 / 안전기준점수 파싱, 전체 이력 테이블(최대 100건) 파싱 및 행 클릭
- 점검 상세 내역 화면: 사용자 정보, 요약 결과, 전체 열기/닫기 및 개별 아코디언 토글, 항목별 상세 설명 파싱
- 엑셀 내보내기: 엑셀 아이콘 클릭 -> '#32770' 저장 다이얼로그 제어 -> 바탕화면 저장 -> 완료 팝업 확인
"""

import ctypes
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import win32con
import win32gui
import winreg
from pywinauto import Application

from pages.client.main_page import MainPage


def get_user_desktop_dir() -> Path:
    """현재 Windows 사용자의 실제 바탕화면 경로를 반환합니다."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        ) as key:
            raw_path, _ = winreg.QueryValueEx(key, "Desktop")
            expanded = os.path.expandvars(raw_path)
            if expanded:
                return Path(expanded)
    except Exception:
        pass
    return Path.home() / "Desktop"


class HistoryPage(MainPage):
    """'점검이력' 탭 전용 Page Object (MainPage 공통 기능 상속)"""

    TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$")

    @staticmethod
    def _parse_int_unit(text: str, unit: str) -> Optional[int]:
        """'88점', '41건' 등에서 정수값을 추출합니다."""
        cleaned = (text or "").strip()
        m = re.fullmatch(rf"(\d+)\s*{re.escape(unit)}", cleaned)
        return int(m.group(1)) if m else None

    def is_detail_view(self) -> bool:
        """현재 화면이 '점검 상세 내역' 뷰인지 여부를 반환합니다."""
        _, win = self._connect_window()
        for t in win.descendants(control_type="Text"):
            if (t.element_info.name or "").strip() == "점검 상세 내역":
                return True
        return False

    def wait_for_history_list_ready(self, timeout: float = 12.0) -> Dict[str, Any]:
        """'점검이력' 목록 화면 DOM(최근점검일시, 안전기준점수, 이력 테이블) 렌더링 완료 대기"""
        deadline = time.time() + timeout
        last_header: Dict[str, Any] = {}
        while True:
            try:
                if self.get_active_tab_name() == "점검이력" and not self.is_detail_view():
                    _, win = self._connect_window()
                    has_table_header = any(
                        (d.element_info.name or "").strip() == "점검 일시"
                        for d in win.descendants(control_type="DataItem")
                    )
                    last_header = self.get_header_info()
                    if has_table_header and last_header.get("safety_score") is not None:
                        time.sleep(0.3)
                        return last_header
            except Exception:
                pass
            if time.time() >= deadline:
                raise TimeoutError(f"'점검이력' 목록 화면 로딩 대기 시간 초과: 마지막 헤더={last_header}")
            time.sleep(0.35)

    def get_header_info(self) -> Dict[str, Any]:
        """
        '점검이력' 목록 상단의 최근점검일시 및 우측 상단 안전기준점수 파싱:
        {"last_inspection_time": "2026-11-16 11:02:40", "safety_score": 100}
        """
        _, win = self._connect_window()
        texts = [
            (t.element_info.name or "").strip()
            for t in win.descendants(control_type="Text")
            if t.element_info.name
        ]
        last_time: Optional[str] = None
        safety_score: Optional[int] = None

        for i, txt in enumerate(texts):
            if txt.startswith("최근점검일시:") and last_time is None:
                val = txt.split("최근점검일시:", 1)[1].strip()
                last_time = val or (texts[i + 1] if i + 1 < len(texts) else None)
            elif txt == "최근점검일시" and i + 1 < len(texts) and last_time is None:
                last_time = texts[i + 1]
            elif "안전기준점수" in txt and safety_score is None:
                m = re.search(r"안전기준점수\s*(\d+)\s*점", txt)
                if m:
                    safety_score = int(m.group(1))
                elif i + 1 < len(texts) and texts[i + 1].isdigit():
                    safety_score = int(texts[i + 1])

        return {
            "last_inspection_time": last_time,
            "safety_score": safety_score,
        }

    def get_all_history_records(self) -> List[Dict[str, Any]]:
        """
        '점검이력' 목록 테이블의 전체 행을 파싱하여 반환합니다.
        반환 형식: [{"no": 1, "inspection_time": "...", "score": 88, "score_text": "88점",
                    "safe_count": 41, "vulnerable_count": 12, "unable_count": 0, "uninspected_count": 0}, ...]
        """
        _, win = self._connect_window()
        items = [
            (d.element_info.name or "").strip()
            for d in win.descendants(control_type="DataItem")
        ]

        records: List[Dict[str, Any]] = []
        i = 0
        while i < len(items):
            cell = items[i]
            if self.TIMESTAMP_RE.match(cell):
                no_str = items[i - 1] if i - 1 >= 0 else ""
                score_text = items[i + 1] if i + 1 < len(items) else ""
                safe_text = items[i + 2] if i + 2 < len(items) else ""
                vuln_text = items[i + 3] if i + 3 < len(items) else ""
                unable_text = items[i + 4] if i + 4 < len(items) else ""
                uninsp_text = items[i + 5] if i + 5 < len(items) else ""

                records.append({
                    "no": int(no_str) if no_str.isdigit() else None,
                    "inspection_time": cell,
                    "score": self._parse_int_unit(score_text, "점"),
                    "score_text": score_text,
                    "safe_count": self._parse_int_unit(safe_text, "건"),
                    "safe_text": safe_text,
                    "vulnerable_count": self._parse_int_unit(vuln_text, "건"),
                    "vulnerable_text": vuln_text,
                    "unable_count": self._parse_int_unit(unable_text, "건"),
                    "unable_text": unable_text,
                    "uninspected_count": self._parse_int_unit(uninsp_text, "건"),
                    "uninspected_text": uninsp_text,
                })
                i += 6
                continue
            i += 1
        return records

    def click_history_row(self, row_index: int = 0, timeout: float = 12.0) -> None:
        """
        '점검이력' 목록 테이블에서 지정 인덱스(0=가장 최근 1번 행)를 클릭하여
        '점검 상세 내역' 화면으로 이동합니다.
        """
        target_h, win = self._connect_window()
        timestamp_cells = [
            d for d in win.descendants(control_type="DataItem")
            if self.TIMESTAMP_RE.match((d.element_info.name or "").strip())
        ]
        if not timestamp_cells:
            raise RuntimeError("'점검이력' 목록 테이블에 클릭할 이력 행이 없습니다.")
        if not (0 <= row_index < len(timestamp_cells)):
            raise IndexError(f"점검이력 행 인덱스 범위 초과 (0~{len(timestamp_cells)-1}): {row_index}")

        target_cell = timestamp_cells[row_index]
        print(f">>> [HistoryPage] {row_index + 1}번째 이력 행('{target_cell.element_info.name}') 클릭...")
        self._click_element(target_cell, target_h)
        self.wait_for_detail_ready(timeout=timeout)

    def wait_for_detail_ready(self, timeout: float = 12.0) -> None:
        """'점검 상세 내역' 화면 DOM 렌더링 완료 대기"""
        deadline = time.time() + timeout
        while True:
            try:
                if self.get_active_tab_name() == "점검이력" and self.is_detail_view():
                    user_info = self.get_detail_user_info()
                    summary = self.get_detail_summary()
                    if user_info.get("inspection_time") and summary.get("score") is not None:
                        time.sleep(0.3)
                        return
            except Exception:
                pass
            if time.time() >= deadline:
                raise TimeoutError("'점검 상세 내역' 화면 DOM 로딩 대기 시간 초과")
            time.sleep(0.35)

    def ensure_latest_detail_view(self, timeout: float = 12.0) -> None:
        """현재 '점검 상세 내역' 화면에 있지 않다면 '점검이력' 탭의 1번(최신) 행을 클릭해 진입합니다."""
        if self.get_active_tab_name() != "점검이력":
            self.navigate_to_tab("점검이력", timeout=timeout)
        if not self.is_detail_view():
            self.wait_for_history_list_ready(timeout=timeout)
            self.click_history_row(row_index=0, timeout=timeout)

    def click_back_to_list(self, timeout: float = 10.0) -> None:
        """'점검 상세 내역' 좌상단 뒤로가기 링크 클릭 후 목록 복귀 대기"""
        target_h, win = self._connect_window()
        for link in win.descendants(control_type="Hyperlink"):
            if "back-link" in (link.element_info.class_name or ""):
                try:
                    link.invoke()
                except Exception:
                    self._click_element(link, target_h)
                self.wait_for_history_list_ready(timeout=timeout)
                return
        raise RuntimeError("'점검 상세 내역'에서 뒤로가기(back-link) 요소를 찾을 수 없습니다.")

    def get_detail_user_info(self) -> Dict[str, str]:
        """
        '점검 상세 내역'의 '사용자 정보' 테이블 파싱:
        점검일시, 사용자 IP, 사용자명, 부서명, OS 정보, 바이러스백신, 버전
        """
        _, win = self._connect_window()
        tables = list(win.descendants(control_type="Table"))
        if not tables:
            return {}

        cells = [
            (d.element_info.name or "").strip()
            for d in tables[0].descendants(control_type="DataItem")
        ]
        key_map = {
            "점검일시": "inspection_time",
            "사용자 IP": "ip",
            "사용자명": "username",
            "부서명": "department",
            "OS 정보": "os",
            "바이러스백신": "antivirus",
            "버전": "version",
        }
        info: Dict[str, str] = {}
        for i, label in enumerate(cells):
            if label in key_map and i + 1 < len(cells):
                info[key_map[label]] = cells[i + 1]
        return info

    def get_detail_summary(self) -> Dict[str, Any]:
        """
        '점검 상세 내역'의 'PC 보안점검 점검 결과' 요약 테이블(.summary-table) 파싱:
        결과(점), 안전(건), 취약(건), 점검불가(건), 미점검(건)
        """
        _, win = self._connect_window()
        summary_table = None
        for tbl in win.descendants(control_type="Table"):
            if "summary-table" in (tbl.element_info.class_name or ""):
                summary_table = tbl
                break

        if summary_table is None:
            return {}

        cells = [
            (d.element_info.name or "").strip()
            for d in summary_table.descendants(control_type="DataItem")
            if (d.element_info.name or "").strip()
        ]
        # 헤더: ['결과', '안전', '취약', '점검불가', '미점검'] + 값: ['88점', '41건', '12건', '0건', '0건']
        if "결과" in cells:
            idx = cells.index("결과")
            values = cells[idx + 5: idx + 10]
            if len(values) == 5:
                return {
                    "score_text": values[0],
                    "score": self._parse_int_unit(values[0], "점"),
                    "safe_text": values[1],
                    "safe_count": self._parse_int_unit(values[1], "건"),
                    "vulnerable_text": values[2],
                    "vulnerable_count": self._parse_int_unit(values[2], "건"),
                    "unable_text": values[3],
                    "unable_count": self._parse_int_unit(values[3], "건"),
                    "uninspected_text": values[4],
                    "uninspected_count": self._parse_int_unit(values[4], "건"),
                }
        return {}

    def get_toggle_all_button_state(self) -> Tuple[Any, str]:
        """'점검 상세 내역'의 '전체 열기' / '전체 닫기' 토글 버튼 (요소, 현재 라벨) 반환"""
        _, win = self._connect_window()
        for b in win.descendants(control_type="Button"):
            if "toggle-btn" in (b.element_info.class_name or ""):
                return b, (b.element_info.name or "").strip()
        raise RuntimeError("'점검 상세 내역'에서 전체 열기/닫기(toggle-btn) 버튼을 찾을 수 없습니다.")

    def click_toggle_all(self, expected_next_label: Optional[str] = None, timeout: float = 6.0) -> str:
        """'전체 열기' / '전체 닫기' 토글 버튼을 클릭하고 라벨 전환 완료까지 대기합니다."""
        target_h, _ = self._connect_window()
        btn, before_label = self.get_toggle_all_button_state()
        print(f">>> [HistoryPage] 토글 버튼 '{before_label}' 클릭...")
        self._click_element(btn, target_h)

        deadline = time.time() + timeout
        while time.time() < deadline:
            _, current_label = self.get_toggle_all_button_state()
            if expected_next_label:
                if current_label == expected_next_label:
                    time.sleep(0.3)
                    return current_label
            elif current_label != before_label:
                time.sleep(0.3)
                return current_label
            time.sleep(0.2)

        _, final_label = self.get_toggle_all_button_state()
        raise TimeoutError(
            f"토글 버튼 상태 전환 대기 시간 초과: 이전='{before_label}', 기대='{expected_next_label}', 현재='{final_label}'"
        )

    def get_detail_items(self) -> List[Dict[str, Any]]:
        """
        '점검 상세 내역'의 아코디언 항목 전체 목록을 파싱합니다.
        반환 형식: [{"no": 1, "status": "안전", "title": "...", "arrow": "▲"/"▼",
                    "is_open": bool, "description": str | None}, ...]
        """
        _, win = self._connect_window()
        container = win
        for grp in win.descendants(control_type="Group"):
            if (grp.element_info.class_name or "") == "main":
                container = grp
                break

        desc = list(container.descendants())

        start_idx = 0
        for idx, elem in enumerate(desc):
            if elem.element_info.control_type == "Button" and "toggle-btn" in (elem.element_info.class_name or ""):
                start_idx = idx + 1
                break

        items: List[Dict[str, Any]] = []
        i = start_idx
        while i < len(desc):
            elem = desc[i]
            if elem.element_info.control_type == "Group" and "accordion-header" in (elem.element_info.class_name or ""):
                header_texts: List[str] = []
                j = i + 1
                while j < len(desc):
                    nxt = desc[j]
                    nxt_ct = nxt.element_info.control_type
                    nxt_cls = nxt.element_info.class_name or ""
                    if nxt_ct == "Group" and "accordion-header" in nxt_cls:
                        break
                    if nxt_ct == "Text":
                        txt = (nxt.element_info.name or "").strip()
                        if txt:
                            header_texts.append(txt)
                    j += 1

                # header_texts는 닫힘 시 4개([no, status, title, '▼']), 열림 시 5개([no, status, title, '▲', description...])
                no_val = int(header_texts[0]) if len(header_texts) >= 1 and header_texts[0].isdigit() else None
                status_val = header_texts[1] if len(header_texts) >= 2 else ""
                title_val = header_texts[2] if len(header_texts) >= 3 else ""
                arrow_val = header_texts[3] if len(header_texts) >= 4 else ""
                desc_val = "\n".join(header_texts[4:]).strip() if len(header_texts) >= 5 else None

                items.append({
                    "no": no_val,
                    "status": status_val,
                    "title": title_val,
                    "arrow": arrow_val,
                    "is_open": arrow_val == "▲",
                    "description": desc_val,
                })
                i = j
                continue
            i += 1
        return items

    def click_item_accordion(self, item_no: int, timeout: float = 5.0) -> None:
        """지정 번호(item_no)의 아코디언 헤더를 클릭하여 개별 항목을 열고 닫히거나 열릴 때까지 대기합니다."""
        before_items = {it["no"]: it["is_open"] for it in self.get_detail_items() if it["no"] is not None}
        before_open = before_items.get(item_no)

        target_h, win = self._connect_window()
        clicked = False
        desc = list(win.descendants())
        for i, elem in enumerate(desc):
            if elem.element_info.control_type == "Group" and "accordion-header" in (elem.element_info.class_name or ""):
                for j in range(i + 1, min(len(desc), i + 5)):
                    if desc[j].element_info.control_type == "Text":
                        if (desc[j].element_info.name or "").strip() == str(item_no):
                            print(f">>> [HistoryPage] {item_no}번 아코디언 헤더 클릭...")
                            self._click_element(elem, target_h)
                            clicked = True
                            break
                        break
            if clicked:
                break
        if not clicked:
            raise RuntimeError(f"'점검 상세 내역'에서 {item_no}번 아코디언 항목을 찾을 수 없습니다.")

        if before_open is None:
            time.sleep(0.4)
            return

        deadline = time.time() + timeout
        while time.time() < deadline:
            cur_items = {it["no"]: it["is_open"] for it in self.get_detail_items() if it["no"] is not None}
            if cur_items.get(item_no) is not None and cur_items[item_no] != before_open:
                return
            time.sleep(0.15)
        raise TimeoutError(f"{item_no}번 아코디언 상태 전환 대기 시간 초과")

    def click_excel_export_icon(self) -> None:
        """'점검 상세 내역' 우측 상단의 엑셀(Microsoft Excel) 아이콘을 클릭합니다."""
        self.bring_to_front()
        target_h, win = self._connect_window()
        for img in win.descendants(control_type="Image"):
            if (img.element_info.name or "").strip() == "Microsoft Excel":
                print(f">>> [HistoryPage] 우측 상단 엑셀 아이콘 클릭: {img.rectangle()}")
                self._click_element(img, target_h)
                return
        raise RuntimeError("'점검 상세 내역' 우측 상단에서 'Microsoft Excel' 아이콘을 찾을 수 없습니다.")

    def _find_save_as_dialog(self, timeout: float = 10.0) -> int:
        """Windows '다른 이름으로 저장'(#32770) 다이얼로그 핸들을 대기 후 반환합니다."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            found_hwnd = 0

            def _cb(h, _):
                nonlocal found_hwnd
                if win32gui.IsWindowVisible(h) and win32gui.GetClassName(h) == "#32770":
                    title = win32gui.GetWindowText(h) or ""
                    if any(k in title for k in ("저장", "Save")):
                        found_hwnd = h

            win32gui.EnumWindows(_cb, None)
            if found_hwnd:
                time.sleep(0.4)
                return found_hwnd
            time.sleep(0.25)
        raise TimeoutError("엑셀 아이콘 클릭 후 '다른 이름으로 저장'(#32770) 다이얼로그가 열리지 않았습니다.")

    @staticmethod
    def _find_filename_edit_and_save_btn(dlg_hwnd: int):
        """
        #32770 다이얼로그에서 파일명 입력 Edit 및 저장 버튼을 탐색합니다.
        UIA 백엔드의 COM 인터페이스 충돌(0x80040155, 0x8001010d fatal exception 콘솔 덤프)을
        방지하기 위해 표준 win32 백엔드를 우선 사용합니다.
        """
        try:
            dlg_app = Application(backend="win32").connect(handle=dlg_hwnd)
            dlg_win = dlg_app.window(handle=dlg_hwnd)

            filename_edit = None
            # standard win32 File Dialog Edit control (id 1148 or 1001 or class Edit)
            for ctrl in dlg_win.children(class_name="Edit"):
                ctrl_id = ctrl.control_id()
                if ctrl_id in (1148, 1001) or "Edit" in ctrl.friendly_class_name():
                    filename_edit = ctrl
                    break
            if filename_edit is None:
                edits = dlg_win.children(class_name="Edit")
                if edits:
                    filename_edit = edits[0]

            save_btn = None
            for bt in dlg_win.children(class_name="Button"):
                bt_text = (bt.window_text() or "").strip()
                bt_id = bt.control_id()
                if bt_id == 1 or bt_text in ("저장(&S)", "저장(S)", "저장", "&Save", "Save"):
                    save_btn = bt
                    break

            if filename_edit is not None and save_btn is not None:
                return dlg_win, filename_edit, save_btn
        except Exception:
            pass

        # Fallback to UIA if win32 lookup fails
        dlg_app = Application(backend="uia").connect(handle=dlg_hwnd)
        dlg_win = dlg_app.window(handle=dlg_hwnd)

        filename_edit = None
        for ed in dlg_win.descendants(control_type="Edit"):
            ed_name = (ed.element_info.name or "").strip()
            ed_aid = (ed.element_info.automation_id or "").strip()
            if "파일 이름" in ed_name or "File name" in ed_name or ed_aid in ("1001", "1148"):
                if "주소" not in ed_name:
                    filename_edit = ed
                    break

        save_btn = None
        for bt in dlg_win.descendants(control_type="Button"):
            bt_name = (bt.element_info.name or "").strip()
            if bt_name in ("저장(S)", "저장(&S)", "저장", "Save"):
                save_btn = bt
                break

        return dlg_win, filename_edit, save_btn

    def save_excel_to_desktop(
        self,
        desktop_dir: Optional[Path] = None,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """
        열린 '다른 이름으로 저장'(#32770) 다이얼로그에서:
        1) 기본 파일명(예: 내PC보안점검_YYYYMMDD_HHMMSS.xlsx)을 읽고
        2) 바탕화면 경로(<desktop_dir>/<filename>)로 지정해 저장합니다.
        """
        dlg_hwnd = self._find_save_as_dialog(timeout=timeout)
        target_dir = desktop_dir or get_user_desktop_dir()
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            _, filename_edit, save_btn = self._find_filename_edit_and_save_btn(dlg_hwnd)
            if filename_edit is None or save_btn is None:
                raise PermissionError(
                    "파일 저장 다이얼로그(#32770) 내부 컨트롤에 접근할 수 없습니다. "
                    "보안점검 프로그램과 동일한 관리자 권한(Run as Administrator)으로 실행했는지 확인하십시오."
                )

            try:
                default_raw = filename_edit.get_value()
            except Exception:
                default_raw = filename_edit.window_text()
            default_filename = os.path.basename((default_raw or "").strip())
            if not default_filename:
                raise RuntimeError("저장 다이얼로그의 기본 파일명 입력란이 비어 있습니다.")

            if not default_filename.lower().endswith(".xlsx"):
                default_filename += ".xlsx"

            save_path = target_dir / default_filename
            if save_path.exists():
                save_path.unlink()

            print(f">>> [HistoryPage] 엑셀 저장 경로 입력: {save_path}")
            filename_edit.set_edit_text(str(save_path))
            time.sleep(0.3)

            try:
                save_btn.click()
            except Exception:
                save_btn.invoke()
        except PermissionError:
            raise
        except Exception as exc:
            err_no = getattr(exc, "winerror", None)
            if err_no == 5 or "액세스가 거부" in str(exc) or "Access is denied" in str(exc):
                raise PermissionError(
                    "Windows UIPI 제약으로 인해 저장 다이얼로그(#32770) 제어 권한이 거부되었습니다. "
                    "관리자 권한 PowerShell에서 실행하십시오."
                ) from exc
            raise

        # 저장 다이얼로그 닫힘 대기 (덮어쓰기 확인 창 동시 감시)
        close_deadline = time.time() + timeout
        handled_overwrite = False
        while time.time() < close_deadline:
            if not win32gui.IsWindow(dlg_hwnd) or not win32gui.IsWindowVisible(dlg_hwnd):
                return {
                    "default_filename": default_filename,
                    "saved_path": save_path,
                }
            if not handled_overwrite:
                overwrite_hwnd = 0

                def _ow_cb(h, _):
                    nonlocal overwrite_hwnd
                    if h != dlg_hwnd and win32gui.IsWindowVisible(h) and win32gui.GetClassName(h) == "#32770":
                        if "확인" in (win32gui.GetWindowText(h) or ""):
                            overwrite_hwnd = h

                win32gui.EnumWindows(_ow_cb, None)
                if overwrite_hwnd:
                    ow_app = Application(backend="uia").connect(handle=overwrite_hwnd)
                    ow_win = ow_app.window(handle=overwrite_hwnd)
                    for bt in ow_win.descendants(control_type="Button"):
                        if (bt.element_info.name or "").strip() in ("예(Y)", "예", "Yes"):
                            bt.invoke()
                            handled_overwrite = True
                            break
            time.sleep(0.2)

        raise TimeoutError("저장 다이얼로그(#32770)가 제한 시간 내에 닫히지 않았습니다.")

    def wait_for_excel_save_popup(self, timeout: float = 8.0) -> str:
        """
        엑셀 저장 완료 팝업('"점검 내역을 엑셀 파일로 저장했습니다."')을 감지해
        메시지를 반환하고 '확인' 버튼을 클릭한 뒤 팝업이 닫힐 때까지 대기합니다.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            # 1. 웹뷰 내 HTML 모달 확인
            target_h, win = self._connect_window()
            texts = [
                (t.element_info.name or "").strip()
                for t in win.descendants(control_type="Text")
                if t.element_info.name
            ]
            matched = [t for t in texts if "엑셀" in t and "저장" in t]
            if matched:
                msg = "\n".join(matched)
                for b in win.descendants(control_type="Button"):
                    if (b.element_info.name or "").strip() == "확인":
                        print(f">>> [HistoryPage] 엑셀 저장 완료 팝업 확인 클릭: {msg!r}")
                        self._click_element(b, target_h)
                        close_dl = time.time() + 3.0
                        while time.time() < close_dl:
                            _, win_chk = self._connect_window()
                            chk_texts = [
                                (t.element_info.name or "").strip()
                                for t in win_chk.descendants(control_type="Text")
                                if t.element_info.name
                            ]
                            if not any("엑셀" in t and "저장" in t for t in chk_texts):
                                break
                            time.sleep(0.15)
                        return msg

            # 2. Win32 #32770 알림 팝업 fallback 확인
            popup_hwnd = 0

            def _cb(h, _):
                nonlocal popup_hwnd
                if win32gui.IsWindowVisible(h) and win32gui.GetClassName(h) == "#32770":
                    child_texts = []
                    win32gui.EnumChildWindows(
                        h,
                        lambda ch, _: child_texts.append((win32gui.GetWindowText(ch) or "").strip()),
                        None,
                    )
                    if any("엑셀" in ct and "저장" in ct for ct in child_texts):
                        popup_hwnd = h

            win32gui.EnumWindows(_cb, None)
            if popup_hwnd:
                p_app = Application(backend="uia").connect(handle=popup_hwnd)
                p_win = p_app.window(handle=popup_hwnd)
                msg_parts = [
                    (t.element_info.name or "").strip()
                    for t in p_win.descendants(control_type="Text")
                    if t.element_info.name
                ]
                for bt in p_win.descendants(control_type="Button"):
                    if (bt.element_info.name or "").strip() in ("확인", "OK"):
                        bt.invoke()
                        close_dl = time.time() + 3.0
                        while time.time() < close_dl:
                            if not win32gui.IsWindow(popup_hwnd) or not win32gui.IsWindowVisible(popup_hwnd):
                                break
                            time.sleep(0.15)
                        break
                return "\n".join(msg_parts)

            time.sleep(0.2)

        raise TimeoutError("엑셀 저장 완료 팝업('점검 내역을 엑셀 파일로 저장했습니다.')이 나타나지 않았습니다.")

