"""
내PC보안점검(taKeeper.exe) UIA 요소 덤프 도구
- 현재 화면에 열려 있는 '내PC보안점검' 메인 창 및 크롬 웹뷰(Chrome_WidgetWin_1)의
  모든 UI Automation 컨트롤(타입, 이름, 좌표)을 콘솔과 파일로 덤프합니다.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.desktop_utils import switch_to_user_desktop

switch_to_user_desktop()

import win32gui
from pywinauto import Application


def find_target_hwnd():
    main_hwnd = None

    def cb(h, extra):
        nonlocal main_hwnd
        if win32gui.IsWindowVisible(h) and "내PC보안점검" in win32gui.GetWindowText(h):
            main_hwnd = h

    win32gui.EnumWindows(cb, None)
    if not main_hwnd:
        return None, None

    chrome_hwnd = None

    def cb_child(ch, extra):
        nonlocal chrome_hwnd
        if "Chrome_WidgetWin_1" in win32gui.GetClassName(ch):
            chrome_hwnd = ch

    win32gui.EnumChildWindows(main_hwnd, cb_child, None)
    return main_hwnd, (chrome_hwnd or main_hwnd)


def dump_uia_elements(output_path: Path = ROOT_DIR / "reports" / "window_elements.txt") -> None:
    main_hwnd, target_hwnd = find_target_hwnd()
    print(f"Main HWND: {main_hwnd}, Target WebView HWND: {target_hwnd}")
    if not target_hwnd:
        print("'내PC보안점검' 실행 창을 찾을 수 없습니다.")
        sys.exit(1)

    app = Application(backend="uia").connect(handle=target_hwnd)
    win = app.window(handle=target_hwnd)
    desc = win.descendants()
    print(f"Total elements: {len(desc)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for i, d in enumerate(desc):
            try:
                line = (
                    f"[{i}] type={d.element_info.control_type}, "
                    f"name='{d.element_info.name}', rect={d.rectangle()}\n"
                )
                f.write(line)
                if i < 40 or any(k in (d.element_info.name or "") for k in ("점검", "시작", "안전", "취약")):
                    print(line.strip())
            except Exception as exc:
                f.write(f"[{i}] err: {exc}\n")

    print(f"UIA 덤프 저장 완료: {output_path}")


if __name__ == "__main__":
    dump_uia_elements()

