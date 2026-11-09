import sys
sys.path.append('.')
from core.desktop_utils import switch_to_user_desktop
switch_to_user_desktop()

import time
import win32gui
from pywinauto import Application
from os_handlers.screen_saver import ScreenSaverHandler
from pages.main_page import MainPage

# 1. 취약 상태 설정
ScreenSaverHandler.set_vulnerable(timeout_minutes=15, lock_on_resume=False)

def find_main():
    res = []
    def cb(h, extra):
        if win32gui.IsWindowVisible(h) and "내PC보안점검" in win32gui.GetWindowText(h):
            res.append(h)
    win32gui.EnumWindows(cb, None)
    return res[0]

hwnd = find_main()
main_page = MainPage(hwnd)
main_page.click_start_inspection()
main_page.wait_for_inspection_done(12)

# 점검결과 창에서 7번 항목 행의 모든 요소 덤프
def get_target():
    res = []
    def cbc(ch, extra):
        if "Chrome_WidgetWin_1" in win32gui.GetClassName(ch):
            res.append(ch)
    win32gui.EnumChildWindows(hwnd, cbc, None)
    return res[0]

th = get_target()
app = Application(backend="uia").connect(handle=th)
win = app.window(handle=th)

# 점검결과 메뉴 클릭
for link in win.descendants(control_type="Hyperlink"):
    if link.element_info.name == "점검결과":
        link.invoke()
        time.sleep(2)
        break

desc = win.descendants()
with open(r"d:\psi_automation\reports\vulnerable_item_7.txt", "w", encoding="utf-8") as f:
    for i, d in enumerate(desc):
        if "화면" in d.element_info.name or "보호기" in d.element_info.name:
            print(f"Item found at index {i}: '{d.element_info.name}'")
            for k in range(max(0, i-5), min(len(desc), i+20)):
                line = f"[{k}] type={desc[k].element_info.control_type}, name='{desc[k].element_info.name}', rect={desc[k].rectangle()}"
                print(line)
                f.write(line + "\n")

