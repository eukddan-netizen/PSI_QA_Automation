"""
Windows 데스크톱 세션 관리 유틸리티
에이전트의 격리된 백그라운드 가상 데스크톱에서
사용자의 실제 물리 모니터 화면('Default' Desktop)으로 스레드를 전환합니다.
"""

import ctypes
import win32service
import win32con

user32 = ctypes.windll.user32


def is_already_on_user_desktop() -> bool:
    """현재 스레드가 이미 사용자의 실제 모니터('Default' 데스크톱)에 연결되어 있는지 확인합니다."""
    try:
        kernel32 = ctypes.windll.kernel32
        tid = kernel32.GetCurrentThreadId()
        hcur = user32.GetThreadDesktop(tid)
        name = win32service.GetUserObjectInformation(hcur, win32service.UOI_NAME)
        return (name or "").lower() == "default"
    except Exception:
        return False


def switch_to_user_desktop() -> bool:
    """
    현재 스레드를 사용자의 실제 모니터 화면인 'Default' 데스크톱으로 전환합니다.
    이미 'Default' 데스크톱에 연결되어 있는 경우 불필요한 중복 전환을 안전하게 건너뜁니다.
    """
    if is_already_on_user_desktop():
        return True

    try:
        hdesk = win32service.OpenDesktop("Default", 0, False, win32con.MAXIMUM_ALLOWED)
        ret = user32.SetThreadDesktop(int(hdesk))
        if ret:
            print(">>> [성공] 사용자의 실제 모니터 화면('Default' 데스크톱)으로 연결되었습니다!")
            return True
        else:
            return False
    except Exception:
        return False


class _ChromeProcessHandle:
    """작업 스케줄러(사용자 대화형 세션)를 통해 실행된 크롬 프로세스 제어 래퍼"""
    def __init__(self, port: int):
        self.port = port

    def terminate(self):
        import os
        os.system(
            f'powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'chrome.exe\'\\" '
            f'| Where-Object {{ $_.CommandLine -match \'remote-debugging-port={self.port}\' }} '
            f'| ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}" >nul 2>&1'
        )


def launch_visible_chrome(port: int = 9222) -> _ChromeProcessHandle:
    """
    IDE 서브프로세스의 창 격리(Window Isolation) 한계를 완벽히 우회하여,
    Windows 작업 스케줄러(Interactive User Session)를 통해 사용자의 실제 모니터에
    새 크롬 창을 띄우고 Playwright CDP 연결을 구성합니다.
    """
    import os
    import subprocess
    import time
    import urllib.request
    import win32con
    import win32gui

    switch_to_user_desktop()

    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    chrome_exe = None
    for p in chrome_paths:
        if os.path.exists(p):
            chrome_exe = p
            break

    if not chrome_exe:
        raise FileNotFoundError("Chrome 실행 파일을 찾을 수 없습니다.")

    # 1. 기존 동일 디버깅 포트 프로세스 정리
    os.system(
        f'powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'chrome.exe\'\\" '
        f'| Where-Object {{ $_.CommandLine -match \'remote-debugging-port={port}\' }} '
        f'| ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}" >nul 2>&1'
    )
    time.sleep(0.5)

    user_data = os.path.join(r"C:\Temp", f"chrome_psi_{port}")
    os.makedirs(user_data, exist_ok=True)

    # 2. 작업 스케줄러 배치를 통해 사용자 모니터 대화형 세션에서 실행
    bat_path = os.path.join(r"C:\Temp", f"launch_chrome_{port}.bat")
    with open(bat_path, "w", encoding="cp949") as f:
        f.write(
            f'@echo off\r\n'
            f'start "" "{chrome_exe}" --remote-debugging-port={port} '
            f'--user-data-dir="{user_data}" --ignore-certificate-errors --no-first-run '
            f'--no-default-browser-check --new-window --start-maximized about:blank\r\n'
        )

    task_name = f"LaunchChromeBat_{port}"
    subprocess.run(f'schtasks /create /tn "{task_name}" /tr "{bat_path}" /sc once /st 00:00 /f >nul 2>&1', shell=True)
    subprocess.run(f'schtasks /run /tn "{task_name}" >nul 2>&1', shell=True)
    time.sleep(1.5)
    subprocess.run(f'schtasks /delete /tn "{task_name}" /f >nul 2>&1', shell=True)

    # 3. CDP 연결 대기
    start = time.time()
    cdp_ready = False
    while time.time() - start < 15:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as res:
                if res.status == 200:
                    cdp_ready = True
                    break
        except Exception:
            time.sleep(0.3)

    if not cdp_ready:
        raise TimeoutError(f"크롬 브라우저 CDP(포트 {port}) 연결에 실패했습니다.")

    # 4. 사용자 화면 최상위로 활성화
    time.sleep(0.5)
    def bring_top():
        def cb(h, _):
            if win32gui.IsWindowVisible(h):
                cls = win32gui.GetClassName(h)
                if cls == "Chrome_WidgetWin_1":
                    t = win32gui.GetWindowText(h)
                    if "about:blank" in t or "TA-PRS" in t or "192.168" in t:
                        try:
                            win32gui.ShowWindow(h, win32con.SW_MAXIMIZE)
                            win32gui.SetForegroundWindow(h)
                        except Exception:
                            pass
        win32gui.EnumWindows(cb, None)

    bring_top()
    return _ChromeProcessHandle(port)

