import sys
sys.path.append('.')
from core.desktop_utils import switch_to_user_desktop
switch_to_user_desktop()

import time
import ctypes
import win32gui
import win32con
from pywinauto import Application

user32 = ctypes.windll.user32

def find_chrome_render():
    res = []
    def cb_main(h, extra):
        if win32gui.IsWindowVisible(h) and "내PC보안점검" in win32gui.GetWindowText(h):
            def cb_child(ch, extra2):
                if win32gui.GetClassName(ch) == "Chrome_RenderWidgetHostHWND":
                    res.append((h, ch))
            win32gui.EnumChildWindows(h, cb_child, None)
    win32gui.EnumWindows(cb_main, None)
    return res[0] if res else (None, None)

main_hwnd, render_hwnd = find_chrome_render()
print(f"Main HWND: {main_hwnd}, Chrome_Render: {render_hwnd}")

# 전면 활성화
win32gui.ShowWindow(main_hwnd, win32con.SW_RESTORE)
win32gui.ShowWindow(main_hwnd, win32con.SW_SHOW)
win32gui.SetForegroundWindow(main_hwnd)
time.sleep(0.5)

app = Application(backend="uia").connect(handle=render_hwnd)
win = app.window(handle=render_hwnd)

start_btn = None
for b in win.descendants(control_type="Button"):
    if "점검 시작" in b.element_info.name:
        start_btn = b
        break

if start_btn:
    rect = start_btn.rectangle()
    cx = (rect.left + rect.right) // 2
    cy = (rect.top + rect.bottom) // 2
    print(f"Target button rect: {rect}, Center: ({cx}, {cy})")

    # 1. 하드웨어 마우스 커서 이동
    user32.SetCursorPos(cx, cy)
    time.sleep(0.2)
    # 2. 마우스 클릭 이벤트
    user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, cx, cy, 0, 0)
    time.sleep(0.1)
    user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, cx, cy, 0, 0)
    print("Mouse event sent!")

    # 3. UIA Invoke 병행 시도
    try:
        start_btn.invoke()
        print("UIA invoke() executed!")
    except Exception as e:
        print(f"UIA invoke exception: {e}")
