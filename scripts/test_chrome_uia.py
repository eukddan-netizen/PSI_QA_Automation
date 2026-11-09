import sys
sys.path.append('.')
from core.desktop_utils import switch_to_user_desktop
switch_to_user_desktop()

from pywinauto import Application
import win32gui

def find_target():
    res = []
    def cb(h, extra):
        cls = win32gui.GetClassName(h)
        if "Chrome_WidgetWin_1" in cls or "Chrome_RenderWidgetHostHWND" in cls:
            res.append((h, cls, win32gui.GetWindowRect(h)))
    win32gui.EnumChildWindows(1181652, cb, None)
    return res

targets = find_target()
print("Targets:", targets)

for h, cls, rect in targets:
    print(f"\n=== Connecting to {cls} (HWND: {h}) ===")
    try:
        app = Application(backend="uia").connect(handle=h)
        w = app.window(handle=h)
        desc = w.descendants()
        print(f"Descendants count: {len(desc)}")
        for d in desc[:30]:
            print(f"  type={d.element_info.control_type}, name='{d.element_info.name}', rect={d.rectangle()}")
    except Exception as e:
        print(f"Error: {e}")

