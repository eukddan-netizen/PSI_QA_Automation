import sys
sys.path.append('.')
from core.desktop_utils import switch_to_user_desktop
switch_to_user_desktop()

import win32gui

def find_hwnd():
    res = []
    def cb(h, extra):
        if win32gui.IsWindowVisible(h) and "내PC보안점검" in win32gui.GetWindowText(h):
            res.append(h)
    win32gui.EnumWindows(cb, None)
    return res[0] if res else None

hwnd = find_hwnd()
print("Main HWND:", hwnd)

children = []
def enum_child(h, extra):
    cls_name = win32gui.GetClassName(h)
    txt = win32gui.GetWindowText(h)
    rect = win32gui.GetWindowRect(h)
    vis = win32gui.IsWindowVisible(h)
    print(f"Child HWND: {h}, Class: {cls_name}, Visible: {vis}, Rect: {rect}, Text: '{txt}'")
    children.append(h)

win32gui.EnumChildWindows(hwnd, enum_child, None)
print(f"Total child windows: {len(children)}")

