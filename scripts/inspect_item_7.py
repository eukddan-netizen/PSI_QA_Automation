import sys
sys.path.append('.')
from core.desktop_utils import switch_to_user_desktop
switch_to_user_desktop()

import win32gui
from pywinauto import Application

def find_chrome():
    res = []
    def cb(h, extra):
        if win32gui.IsWindowVisible(h) and "내PC보안점검" in win32gui.GetWindowText(h):
            def cbc(ch, extra2):
                if win32gui.GetClassName(ch) == "Chrome_RenderWidgetHostHWND":
                    res.append(ch)
            win32gui.EnumChildWindows(h, cbc, None)
    win32gui.EnumWindows(cb, None)
    return res[0]

ch = find_chrome()
app = Application(backend="uia").connect(handle=ch)
win = app.window(handle=ch)

print("=== Searching for Screen Saver (화면 보호기) ===")
desc = win.descendants()
for i, d in enumerate(desc):
    name = d.element_info.name
    if "화면" in name or "보호기" in name or "7" in name:
        # print neighbor elements
        start = max(0, i - 3)
        end = min(len(desc), i + 6)
        print(f"\n--- Found at index {i}: '{name}' ({d.element_info.control_type}) ---")
        for j in range(start, end):
            print(f"  [{j}] type={desc[j].element_info.control_type}, name='{desc[j].element_info.name}', rect={desc[j].rectangle()}")

