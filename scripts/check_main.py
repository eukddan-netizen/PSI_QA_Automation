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

for d in win.descendants(control_type="Button"):
    print(f"Button: name='{d.element_info.name}', rect={d.rectangle()}")
for d in win.descendants(control_type="Text"):
    if any(k in d.element_info.name for k in ["점검", "일시", "최근"]):
        print(f"Text: '{d.element_info.name}'")

