import sys
sys.path.append('.')
from core.desktop_utils import switch_to_user_desktop
switch_to_user_desktop()

import time
import win32gui
import win32con
from pywinauto import Application

def find_windows():
    main_h = None
    render_h = None
    def cb(h, extra):
        nonlocal main_h, render_h
        if win32gui.IsWindowVisible(h) and "내PC보안점검" in win32gui.GetWindowText(h):
            main_h = h
            def cbc(ch, extra2):
                nonlocal render_h
                if win32gui.GetClassName(ch) == "Chrome_RenderWidgetHostHWND":
                    render_h = ch
            win32gui.EnumChildWindows(h, cbc, None)
    win32gui.EnumWindows(cb, None)
    return main_h, render_h

main_h, render_h = find_windows()
print(f"Main HWND: {main_h}, Render HWND: {render_h}")

# 창 활성화
win32gui.ShowWindow(main_h, win32con.SW_RESTORE)
win32gui.ShowWindow(main_h, win32con.SW_SHOW)
win32gui.SetForegroundWindow(main_h)
time.sleep(0.5)

# Render HWND에서 '▶ 점검 시작' 버튼 찾기
app = Application(backend="uia").connect(handle=render_h)
win = app.window(handle=render_h)

btn = None
for b in win.descendants(control_type="Button"):
    if "점검 시작" in b.element_info.name:
        btn = b
        break

if not btn:
    # 혹시 '메인' 탭이 아닌지 확인
    for link in win.descendants(control_type="Hyperlink"):
        if link.element_info.name == "메인":
            print("Going to 메인 tab...")
            link.invoke()
            time.sleep(1)
            break
    for b in win.descendants(control_type="Button"):
        if "점검 시작" in b.element_info.name:
            btn = b
            break

print("Button:", btn.element_info.name if btn else "None")
if btn:
    rect = btn.rectangle()
    print("Button Screen Rect:", rect)
    # Render HWND 기준 로컬 좌표 계산
    r_rect = win32gui.GetWindowRect(render_h)
    local_x = (rect.left + rect.right) // 2 - r_rect[0]
    local_y = (rect.top + rect.bottom) // 2 - r_rect[1]
    print(f"Render Window Rect: {r_rect}, Local coords: ({local_x}, {local_y})")

    lParam = (local_y << 16) | (local_x & 0xFFFF)
    print("Sending WM_LBUTTONDOWN and WM_LBUTTONUP via PostMessage...")
    win32gui.PostMessage(render_h, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    time.sleep(0.1)
    win32gui.PostMessage(render_h, win32con.WM_LBUTTONUP, 0, lParam)
    print("Messages posted!")

