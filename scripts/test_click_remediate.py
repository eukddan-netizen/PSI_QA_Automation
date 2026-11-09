import sys
sys.path.append('.')
from core.desktop_utils import switch_to_user_desktop
switch_to_user_desktop()

import time
import win32gui
import win32con
from pywinauto import Application
from os_handlers.screen_saver import ScreenSaverHandler

def get_target():
    res = []
    def cb(h, extra):
        if win32gui.IsWindowVisible(h) and "내PC보안점검" in win32gui.GetWindowText(h):
            def cbc(ch, extra2):
                if "Chrome_WidgetWin_1" in win32gui.GetClassName(ch):
                    res.append((h, ch))
            win32gui.EnumChildWindows(h, cbc, None)
    win32gui.EnumWindows(cb, None)
    return res[0] if res else (None, None)

main_h, target_h = get_target()
print(f"Main HWND: {main_h}, Target HWND: {target_h}")

# 창 활성화
win32gui.ShowWindow(main_h, win32con.SW_RESTORE)
win32gui.ShowWindow(main_h, win32con.SW_SHOW)
win32gui.SetForegroundWindow(main_h)
time.sleep(0.5)

app = Application(backend="uia").connect(handle=target_h)
win = app.window(handle=target_h)

# 7번 항목 '화면 보호기' 조치 버튼 탐색
desc = win.descendants()
target_btn = None
for i, d in enumerate(desc):
    if "화면 보호기" in d.element_info.name:
        print(f"Found '화면 보호기' at index {i}")
        # 그 뒤에서 name='조치'인 Button 찾기
        for k in range(i, min(len(desc), i + 10)):
            if desc[k].element_info.control_type == "Button" and desc[k].element_info.name == "조치":
                target_btn = desc[k]
                print(f"Found Action Button: {desc[k].element_info.name} at {desc[k].rectangle()}")
                break
        break

if not target_btn:
    print("Action button '조치' not found!")
    sys.exit(1)

# 클릭 실행
rect = target_btn.rectangle()
r_rect = win32gui.GetWindowRect(target_h)
local_x = (rect.left + rect.right) // 2 - r_rect[0]
local_y = (rect.top + rect.bottom) // 2 - r_rect[1]

print(f"Clicking '조치' button at screen {rect}, local ({local_x}, {local_y})...")
lParam = (local_y << 16) | (local_x & 0xFFFF)
win32gui.PostMessage(target_h, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
time.sleep(0.08)
win32gui.PostMessage(target_h, win32con.WM_LBUTTONUP, 0, lParam)
print("Click message posted!")

# 2초 후 OS 레지스트리 및 UI 상태 확인
time.sleep(2.0)
settings = ScreenSaverHandler.get_settings()
is_safe, msg = ScreenSaverHandler.is_secure()
print(f"\n>>> [조치 직후 OS 상태 검증] 윈도우 설정: {settings}")
print(f">>> [안전 여부]: {is_safe} ({msg})")

# UI 상태 다시 읽기
win2 = app.window(handle=target_h)
desc2 = win2.descendants()
for i, d in enumerate(desc2):
    if "화면 보호기" in d.element_info.name:
        for k in range(i, min(len(desc2), i + 10)):
            print(f"Post-action [{k}] type={desc2[k].element_info.control_type}, name='{desc2[k].element_info.name}'")
        break

