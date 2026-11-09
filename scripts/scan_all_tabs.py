"""
각 메뉴 탭('점검', '점검결과', '설정' 등)을 순회하며 각 화면의 모든 UI 요소를 긁어오는 스캐너
"""

import os
import time
from pywinauto import Application

os.environ["__COMPAT_LAYER"] = "RunAsInvoker"
exe_path = r"C:\Program Files (x86)\topaegis\PRSv5\taKeeper.exe"

print(">>> taKeeper.exe 연결/실행 중...")
try:
    app = Application(backend="uia").connect(path=exe_path)
    print(">>> 이미 실행 중인 창에 연결되었습니다.")
except Exception:
    app = Application(backend="uia").start(f'"{exe_path}"')
    time.sleep(3)

# 메인 윈도우 찾기
main_win = None
for w in app.windows():
    if "내PC보안점검" in w.window_text():
        main_win = w
        break

if not main_win:
    print(">>> '내PC보안점검' 창을 찾지 못했습니다.")
    exit(1)

print(f">>> 메인 윈도우 확인: '{main_win.window_text()}'\n")

tabs_to_scan = ["점검", "점검결과", "점검이력", "PC정리", "설정", "메인"]

for tab_name in tabs_to_scan:
    print(f"\n=======================================================")
    print(f"[{tab_name}] 탭 클릭 및 화면 UI 요소 수집")
    print(f"=======================================================")
    
    found_tab = None
    for link in main_win.descendants(control_type="Hyperlink"):
        if link.element_info.name == tab_name:
            found_tab = link
            break
            
    if not found_tab:
        print(f">>> '{tab_name}' 탭을 찾을 수 없습니다.")
        continue
        
    print(f">>> '{tab_name}' 탭 클릭 (Invoke)...")
    try:
        found_tab.invoke()
    except Exception:
        try:
            found_tab.iface_invoke.Invoke()
        except Exception as e:
            print(f">>> 클릭 실패: {e}")
            continue

    time.sleep(2)  # 화면 전환 대기
    
    # 해당 화면의 전체 컨트롤 수집
    descendants = main_win.descendants()
    print(f">>> '{tab_name}' 화면 총 하위 컨트롤 수: {len(descendants)}")
    
    buttons = []
    texts = []
    others = []
    
    for c in descendants:
        try:
            c_type = c.element_info.control_type
            name = c.element_info.name.strip().replace("\n", " ")
            if not name:
                continue
            if c_type == "Button":
                buttons.append(name)
            elif c_type == "Text":
                texts.append(name)
            elif c_type not in ["Pane", "Document", "Group"]:
                others.append(f"[{c_type}] {name}")
        except Exception:
            pass
            
    print(f"--- [버튼 목록 ({len(buttons)}개)] ---")
    for b in buttons:
        print(f"  • Button: '{b}'")
        
    print(f"--- [기타 상호작용 컨트롤 ({len(others)}개)] ---")
    for o in others[:15]:
        print(f"  • {o}")
        
    print(f"--- [주요 텍스트 ({len(texts)}개 중 상위 15개)] ---")
    for t in texts[:15]:
        print(f"  • '{t}'")

print("\n>>> 모든 화면 스캔 완료!")
