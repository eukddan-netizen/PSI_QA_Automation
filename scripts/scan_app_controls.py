import os
import time
from pywinauto import Application

os.environ["__COMPAT_LAYER"] = "RunAsInvoker"
exe_path = r"C:\Program Files (x86)\topaegis\PRSv5\taKeeper.exe"

print(">>> taKeeper.exe 실행 중 (자동 UAC 우회)...")
app = Application(backend="uia").start(f'"{exe_path}"')
time.sleep(3)

print(">>> 윈도우 및 컨트롤 정밀 스캔 시작...")
for idx, w in enumerate(app.windows()):
    title = w.window_text()
    rect = w.rectangle()
    print(f"\n==========================================")
    print(f"[{idx}] 윈도우 타이틀: '{title}' (크기: {rect.width()}x{rect.height()})")
    print(f"==========================================")
    
    # 하위 모든 컨트롤 가져오기
    try:
        descendants = w.descendants()
        print(f"하위 컨트롤 수: {len(descendants)}")
        for j, c in enumerate(descendants):
            c_type = c.element_info.control_type
            c_name = c.element_info.name
            c_id = c.element_info.automation_id
            c_class = c.element_info.class_name
            # 주요 정보 출력
            print(f"  ({j+1:02d}) [{c_type}] Name='{c_name}' | AutoId='{c_id}' | Class='{c_class}'")
    except Exception as e:
        print(f"  컨트롤 스캔 오류: {e}")

print("\n>>> 스캔 완료!")

