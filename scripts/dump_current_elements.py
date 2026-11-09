import sys
import os
sys.path.append('.')
from core.desktop_utils import switch_to_user_desktop
switch_to_user_desktop()

import win32gui
from pywinauto import Application

def find_hwnd():
    res = []
    def cb(h, extra):
        if win32gui.IsWindowVisible(h) and "내PC보안점검" in win32gui.GetWindowText(h):
            res.append(h)
    win32gui.EnumWindows(cb, None)
    return res[0] if res else None

hwnd = find_hwnd()
print("Found HWND:", hwnd)
if not hwnd:
    sys.exit(1)

app = Application(backend="uia").connect(handle=hwnd)
win = app.window(handle=hwnd)
desc = win.descendants()
print(f"Total elements: {len(desc)}")
with open(r"d:\psi_automation\reports\window_elements.txt", "w", encoding="utf-8") as f:
    for i, d in enumerate(desc):
        try:
            line = f"[{i}] type={d.element_info.control_type}, name='{d.element_info.name}', rect={d.rectangle()}\n"
            f.write(line)
            if i < 40 or "점검" in d.element_info.name or "시작" in d.element_info.name or "13:" in d.element_info.name:
                print(line.strip())
        except Exception as e:
            f.write(f"[{i}] err: {e}\n")

