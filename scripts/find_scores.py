import sys
sys.path.append('.')
from core.desktop_utils import switch_to_user_desktop
switch_to_user_desktop()

import win32gui
from pywinauto import Application

def get_target():
    res = []
    def cb(h, extra):
        if win32gui.IsWindowVisible(h) and "내PC보안점검" in win32gui.GetWindowText(h):
            def cbc(ch, extra2):
                if "Chrome_WidgetWin_1" in win32gui.GetClassName(ch):
                    res.append(ch)
            win32gui.EnumChildWindows(h, cbc, None)
    win32gui.EnumWindows(cb, None)
    return res[0]

th = get_target()
app = Application(backend="uia").connect(handle=th)
win = app.window(handle=th)

for d in win.descendants(control_type="Text"):
    name = d.element_info.name
    if name and any(k in name for k in ["점", "점수", "취약"]):
        print(f"Text: '{name}', rect={d.rectangle()}")

