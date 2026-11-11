"""
Windows 데스크톱 세션 관리 유틸리티
에이전트의 격리된 백그라운드 가상 데스크톱에서
사용자의 실제 물리 모니터 화면('Default' Desktop)으로 스레드를 전환합니다.
"""

import ctypes
import json
import os
import subprocess
import time
from typing import Optional, Set
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


def _get_debug_chrome_pids(port: Optional[int] = None) -> Set[int]:
    """원격 디버깅 포트로 실행된 자동화 전용 chrome.exe 프로세스 PID 목록을 반환합니다."""
    filter_expr = f"remote-debugging-port={port}" if port is not None else "remote-debugging-port="
    ps_cmd = (
        "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" "
        f"| Where-Object {{ $_.CommandLine -match '{filter_expr}' }} "
        "| Select-Object -ExpandProperty ProcessId"
    )
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=5,
        )
        pids: Set[int] = set()
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.isdigit():
                pids.add(int(line))
        return pids
    except Exception:
        return set()


def _stop_debug_chrome(port: int, graceful: bool = True) -> None:
    """지정 디버깅 포트의 자동화 전용 크롬 프로세스를 안전하게 종료합니다."""
    if graceful:
        # 1. 정상 창 닫기(WM_CLOSE)를 먼저 시도하여 Chrome이 exit_type='Normal'로 종료되도록 유도
        graceful_cmd = (
            "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" "
            f"| Where-Object {{ $_.CommandLine -match 'remote-debugging-port={port}' }} "
            "| ForEach-Object { $p = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue; "
            "if ($p -and $p.MainWindowHandle -ne 0) { $null = $p.CloseMainWindow() } }"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", graceful_cmd],
                capture_output=True,
                timeout=4,
            )
            deadline = time.time() + 1.5
            while time.time() < deadline:
                if not _get_debug_chrome_pids(port):
                    return
                time.sleep(0.2)
        except Exception:
            pass

    # 2. 남아있는 프로세스 강제 정리
    force_cmd = (
        "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" "
        f"| Where-Object {{ $_.CommandLine -match 'remote-debugging-port={port}' }} "
        "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    os.system(f'powershell -NoProfile -Command "{force_cmd}" >nul 2>&1')


def _sanitize_chrome_profile(user_data_dir: str) -> None:
    """
    크롬 프로필 Preferences를 사전 정리하여:
    1) 비정상 종료 후 재실행 시 뜨는 '페이지 복구' 버블 방지 (exit_type='Normal', exited_cleanly=True)
    2) 로그인 후 뜨는 '비밀번호 저장' 버블 방지 (credentials_enable_service=False, password_manager_enabled=False)
    """
    default_dir = os.path.join(user_data_dir, "Default")
    os.makedirs(default_dir, exist_ok=True)
    prefs_path = os.path.join(default_dir, "Preferences")

    prefs = {}
    if os.path.exists(prefs_path):
        try:
            with open(prefs_path, "r", encoding="utf-8") as f:
                prefs = json.load(f) or {}
        except Exception:
            prefs = {}

    prefs["credentials_enable_service"] = False
    profile = prefs.setdefault("profile", {})
    if isinstance(profile, dict):
        profile["password_manager_enabled"] = False
        profile["exit_type"] = "Normal"
        profile["exited_cleanly"] = True

    try:
        with open(prefs_path, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False)
    except Exception:
        pass


def _match_chrome_bubble_kind(text_blob: str) -> Optional[str]:
    """문자열에서 Chrome 브라우저 우측 상단 버블('페이지 복구' / '비밀번호 저장') 유형을 판별합니다."""
    lowered = (text_blob or "").lower()
    if any(k in lowered for k in ("복구", "올바르게 종료", "restore pages", "didn't shut down")):
        return "restore"
    if any(k in lowered for k in ("비밀번호 저장", "비밀번호를 저장", "암호 저장", "암호를 저장", "save password")):
        return "save_password"
    return None


def _click_bubble_dismiss_button(container, kind: str, popup_hwnd: Optional[int] = None) -> bool:
    """Chrome 버블 내부의 취소/사용 안 함/닫기(X) 버튼을 찾아 클릭합니다."""
    import win32gui

    if kind == "save_password":
        preferred = (
            "사용 안 함",
            "저장 안 함",
            "안 함",
            "안함",
            "취소",
            "닫기",
            "never",
            "no thanks",
            "cancel",
            "close",
        )
        forbidden = ("저장", "save")
    else:
        preferred = ("닫기", "취소", "아니요", "close", "cancel", "no")
        forbidden = ("복구", "restore")

    try:
        buttons = container.descendants(control_type="Button")
    except Exception:
        buttons = []

    target_btn = None
    # 1차: 정확 일치 우선
    for pref in preferred:
        for b in buttons:
            b_name = (b.element_info.name or "").strip().lower()
            if b_name == pref:
                target_btn = b
                break
        if target_btn is not None:
            break

    # 2차: 부분 일치 (저장/복구 등 긍정 액션 버튼 제외)
    if target_btn is None:
        for pref in preferred:
            for b in buttons:
                b_name = (b.element_info.name or "").strip().lower()
                if not b_name:
                    continue
                if any(f == b_name or (f in b_name and "안" not in b_name and "never" not in b_name) for f in forbidden):
                    continue
                if pref in b_name:
                    target_btn = b
                    break
            if target_btn is not None:
                break

    if target_btn is not None:
        btn_label = (target_btn.element_info.name or "").strip()
        print(f">>> [Chrome] '{kind}' 팝업 닫기 버튼 클릭: '{btn_label}'")
        try:
            target_btn.invoke()
            return True
        except Exception:
            try:
                target_btn.click_input()
                return True
            except Exception:
                pass

    # 3차: 독립 팝업 창인 경우 WM_CLOSE 또는 우측 상단 X 버튼으로 안전 닫기
    if popup_hwnd is not None and win32gui.IsWindow(popup_hwnd):
        if buttons:
            safe_btns = [
                b for b in buttons
                if not any(f in (b.element_info.name or "").strip().lower() for f in forbidden)
            ]
            if safe_btns:
                x_btn = max(safe_btns, key=lambda b: b.rectangle().right)
                try:
                    x_btn.invoke()
                    return True
                except Exception:
                    try:
                        x_btn.click_input()
                        return True
                    except Exception:
                        pass
        try:
            win32gui.PostMessage(popup_hwnd, win32con.WM_CLOSE, 0, 0)
            return True
        except Exception:
            pass

    return False


def dismiss_chrome_bubbles(port: Optional[int] = None, timeout: float = 1.2) -> int:
    """
    자동화 전용 크롬 창(remote-debugging-port) 우측 상단에 노출되는
    '비밀번호 저장' / '페이지 복구' 브라우저 버블을 UIA로 감지하여 자동으로 닫습니다.
    (사용자의 개인 브라우저는 PID 필터로 완전히 제외합니다.)
    """
    import win32gui
    import win32process
    from pywinauto import Application

    switch_to_user_desktop()
    pids = _get_debug_chrome_pids(port=port)
    if not pids:
        return 0

    dismissed = 0
    deadline = time.time() + max(0.1, timeout)

    while time.time() < deadline:
        chrome_hwnds = []

        def _enum_cb(h, _):
            if win32gui.IsWindowVisible(h) and win32gui.GetClassName(h) == "Chrome_WidgetWin_1":
                _, pid = win32process.GetWindowThreadProcessId(h)
                if pid in pids:
                    chrome_hwnds.append(h)

        win32gui.EnumWindows(_enum_cb, None)
        found_this_round = False

        for hwnd in chrome_hwnds:
            try:
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h_len = rect[3] - rect[1]
                title = win32gui.GetWindowText(hwnd) or ""

                app = Application(backend="uia").connect(handle=hwnd)
                win = app.window(handle=hwnd)

                # 케이스 1: 버블 자체가 별도 소형 팝업 Chrome_WidgetWin_1 창으로 뜬 경우
                if w < 700 and h_len < 500:
                    texts = [title]
                    for t in win.descendants(control_type="Text"):
                        if t.element_info.name:
                            texts.append(t.element_info.name)
                    for b in win.descendants(control_type="Button"):
                        if b.element_info.name:
                            texts.append(b.element_info.name)

                    kind = _match_chrome_bubble_kind(" ".join(texts))
                    if kind and _click_bubble_dismiss_button(win, kind, popup_hwnd=hwnd):
                        dismissed += 1
                        found_this_round = True
                        time.sleep(0.3)
                    continue

                # 케이스 2: 메인 브라우저 창 내부의 Dialog / Alert 컨트롤로 뜬 경우
                for ctrl_type in ("Dialog", "Alert"):
                    for dlg in win.descendants(control_type=ctrl_type):
                        texts = [dlg.element_info.name or ""]
                        try:
                            for t in dlg.descendants(control_type="Text"):
                                if t.element_info.name:
                                    texts.append(t.element_info.name)
                            for b in dlg.descendants(control_type="Button"):
                                if b.element_info.name:
                                    texts.append(b.element_info.name)
                        except Exception:
                            pass

                        kind = _match_chrome_bubble_kind(" ".join(texts))
                        if kind and _click_bubble_dismiss_button(dlg, kind):
                            dismissed += 1
                            found_this_round = True
                            time.sleep(0.3)
            except Exception:
                continue

        if found_this_round:
            # 연달아 뜬 두 번째 버블이 없는지 한 번 더 짧게 확인
            time.sleep(0.3)
            continue

        time.sleep(0.3)

    return dismissed


class _ChromeProcessHandle:
    """작업 스케줄러(사용자 대화형 세션)를 통해 실행된 크롬 프로세스 제어 래퍼"""
    def __init__(self, port: int):
        self.port = port

    def terminate(self):
        _stop_debug_chrome(self.port, graceful=True)


def launch_visible_chrome(port: int = 9222) -> _ChromeProcessHandle:
    """
    IDE 서브프로세스의 창 격리(Window Isolation) 한계를 완벽히 우회하여,
    Windows 작업 스케줄러(Interactive User Session)를 통해 사용자의 실제 모니터에
    새 크롬 창을 띄우고 Playwright CDP 연결을 구성합니다.
    """
    import urllib.request
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

    # 1. 기존 동일 디버깅 포트 프로세스 정리 및 프로필 사전 정비
    _stop_debug_chrome(port, graceful=True)
    time.sleep(0.3)

    user_data = os.path.join(r"C:\Temp", f"chrome_psi_{port}")
    os.makedirs(user_data, exist_ok=True)
    _sanitize_chrome_profile(user_data)

    # 2. 작업 스케줄러 배치를 통해 사용자 모니터 대화형 세션에서 실행
    bat_path = os.path.join(r"C:\Temp", f"launch_chrome_{port}.bat")
    with open(bat_path, "w", encoding="cp949") as f:
        f.write(
            f'@echo off\r\n'
            f'start "" "{chrome_exe}" --remote-debugging-port={port} '
            f'--user-data-dir="{user_data}" --ignore-certificate-errors --no-first-run '
            f'--no-default-browser-check --hide-crash-restore-bubble '
            f'--disable-save-password-bubble --new-window --start-maximized about:blank\r\n'
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

    # 4. 사용자 화면 최상위로 활성화 및 혹시 남아있는 브라우저 복구/저장 버블 정리
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
    dismiss_chrome_bubbles(port=port, timeout=1.0)
    return _ChromeProcessHandle(port)

