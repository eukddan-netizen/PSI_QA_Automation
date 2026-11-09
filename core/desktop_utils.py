"""
Windows 데스크톱 세션 관리 유틸리티
에이전트의 격리된 백그라운드 가상 데스크톱에서
사용자의 실제 물리 모니터 화면('Default' Desktop)으로 스레드를 전환합니다.
"""

import ctypes
import win32service
import win32con

user32 = ctypes.windll.user32


def switch_to_user_desktop() -> bool:
    """
    현재 스레드를 사용자의 실제 모니터 화면인 'Default' 데스크톱으로 전환합니다.
    이를 통해 사용자가 보고 있는 모니터 화면에 실제 창을 띄우고 조작할 수 있습니다.
    """
    try:
        hdesk = win32service.OpenDesktop("Default", 0, False, win32con.MAXIMUM_ALLOWED)
        ret = user32.SetThreadDesktop(int(hdesk))
        if ret:
            print(">>> [성공] 사용자의 실제 모니터 화면('Default' 데스크톱)으로 연결되었습니다!")
            return True
        else:
            print(">>> [경고] SetThreadDesktop 실패")
            return False
    except Exception as e:
        print(f">>> [경고] Default 데스크톱 전환 중 오류: {e}")
        return False

