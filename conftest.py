"""
pytest 공통 설정 및 fixture 정의
- state_guard: 각 점검 테스트가 변경한 레지스트리/계정/OS 설정을 테스트 종료 시(실패 포함) 원래 값으로 자동 복구
"""

import ctypes
from ctypes import wintypes
import sys
from pathlib import Path
import pytest

# Testing UI 등 파이프 환경에서도 print() 로그가 즉시 출력되도록 줄 단위 버퍼링 활성화
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(line_buffering=True)
        except Exception:
            pass

# win32gui/pywinauto 임포트 전에 프로세스 DPI 인식을 먼저 활성화 (좌표 밀림 방지)
try:
    _u32 = ctypes.windll.user32
    _u32.SetProcessDpiAwarenessContext.argtypes = [wintypes.HANDLE]
    _u32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
    if not _u32.SetProcessDpiAwarenessContext(wintypes.HANDLE(-4)):
        _u32.SetProcessDPIAware()
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

ROOT_DIR = str(Path(__file__).resolve().parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from common.os_utils import StateGuard
from dashboard.pytest_plugin import configure_dashboard_plugin, register_dashboard_hooks


def pytest_addoption(parser: pytest.Parser) -> None:
    register_dashboard_hooks(parser)


def pytest_configure(config: pytest.Config) -> None:
    configure_dashboard_plugin(config)


@pytest.fixture(scope="function")
def state_guard():
    """
    점검 테스트 실행 전 OS 상태를 백업하고,
    테스트가 실패하거나 중단되어도 Teardown에서 반드시 원래 값으로 복구합니다.
    """
    guard = StateGuard()
    try:
        yield guard
    finally:
        errors = guard.restore_all()
        if errors:
            pytest.fail("OS 설정 원복 중 오류가 발생했습니다:\n" + "\n".join(errors))
