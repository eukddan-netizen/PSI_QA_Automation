import sys
sys.path.append('.')
from core.desktop_utils import switch_to_user_desktop
switch_to_user_desktop()

from pywinauto import Application

app = Application(backend="uia").connect(handle=4523588)
win = app.window(handle=4523588)
desc = win.descendants()

print(f"Total elements: {len(desc)}")
with open(r"d:\psi_automation\reports\elements_4523588.txt", "w", encoding="utf-8") as f:
    for i, d in enumerate(desc):
        try:
            line = f"[{i}] type={d.element_info.control_type}, name='{d.element_info.name}', rect={d.rectangle()}\n"
            f.write(line)
            if "화면" in d.element_info.name or "보호기" in d.element_info.name:
                print(f"MATCH: [{i}] {line.strip()}")
                # print 10 neighbors
                for k in range(max(0, i-5), min(len(desc), i+15)):
                    print(f"   nearby [{k}] type={desc[k].element_info.control_type}, name='{desc[k].element_info.name}', rect={desc[k].rectangle()}")
        except Exception as e:
            f.write(f"[{i}] err: {e}\n")

