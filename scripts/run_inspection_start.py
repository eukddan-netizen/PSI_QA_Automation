"""
관리자 권한으로 실행되어 사용자 모니터의 taKeeper를 제어하고
'▶ 점검 시작' 버튼을 클릭하는 스크립트
"""

import os
import sys
import time

log_file = r"d:\psi_automation\reports\inspection_run.log"
os.makedirs(os.path.dirname(log_file), exist_ok=True)

def log(msg):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S] ")
    line = timestamp + msg
    print(line)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

log(">>> 스크립트 시작 (관리자 권한 승격 실행됨)")

import win32gui
import win32con
from pywinauto import Application, Desktop

# 1. 이미 떠 있는 '내PC보안점검' 창 탐색
log(">>> 사용자 화면의 '내PC보안점검' 창 탐색 중...")
psi_hwnd = None
for _ in range(10):
    def find_win(hwnd, extra):
        global psi_hwnd
        if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
            if "내PC보안점검" in win32gui.GetWindowText(hwnd):
                psi_hwnd = hwnd
    win32gui.EnumWindows(find_win, None)
    if psi_hwnd:
        break
    time.sleep(0.5)

app = None
if psi_hwnd:
    log(f">>> 이미 열려 있는 창 발견! (HWND: {psi_hwnd})")
    app = Application(backend="uia").connect(handle=psi_hwnd)
    main_win = app.window(handle=psi_hwnd)
else:
    log(">>> 창이 열려 있지 않아 새로 taKeeper.exe를 실행합니다...")
    exe_path = r"C:\Program Files (x86)\topaegis\PRSv5\taKeeper.exe"
    app = Application(backend="uia").start(f'"{exe_path}"')
    time.sleep(4)
    main_win = app.window(title="내PC보안점검")

# 2. 창 활성화
try:
    win32gui.ShowWindow(main_win.handle, win32con.SW_RESTORE)
    win32gui.ShowWindow(main_win.handle, win32con.SW_SHOW)
    win32gui.SetForegroundWindow(main_win.handle)
    log(">>> 창을 모니터 전면에 활성화했습니다.")
except Exception as e:
    log(f">>> 창 활성화 예외: {e}")

# 3. '메인' 탭 클릭 (혹시 다른 탭에 있을 경우 대비)
for link in main_win.descendants(control_type="Hyperlink"):
    if link.element_info.name == "메인":
        try:
            link.invoke()
            time.sleep(1)
        except Exception:
            pass
        break

# 4. '▶ 점검 시작' 버튼 클릭
start_btn = None
for btn in main_win.descendants(control_type="Button"):
    if "점검 시작" in btn.element_info.name:
        start_btn = btn
        break

if start_btn:
    log(f">>> '{start_btn.element_info.name}' 버튼을 찾았습니다! 클릭합니다...")
    try:
        start_btn.invoke()
    except Exception:
        start_btn.iface_invoke.Invoke()
    log(">>> [성공!] '▶ 점검 시작' 버튼 클릭 완료!")
    time.sleep(5)
else:
    log(">>> [오류] '▶ 점검 시작' 버튼을 찾지 못했습니다. 버튼 목록:")
    for btn in main_win.descendants(control_type="Button"):
        log(f"  - Button: '{btn.element_info.name}'")

# 5. 화면 스크린샷 저장
screenshot_path = r"d:\psi_automation\reports\real_inspection_result.png"
try:
    main_win.capture_as_image().save(screenshot_path)
    log(f">>> [완료] 화면 캡처 저장: {screenshot_path}")
except Exception as e:
    log(f">>> 캡처 실패: {e}")

log(">>> 스크립트 종료")
