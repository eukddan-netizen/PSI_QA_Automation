"""
taKeeper.exe (보안점검 프로그램) 제어 및 WebView2 CDP 연결 컨트롤러
관리자 권한(UAC) 실행 및 환경 변수 주입 지원
"""

import os
import sys
import time
import winreg
import requests
import subprocess
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page


class AppController:
    DEFAULT_EXE_PATH = r"C:\Program Files (x86)\topaegis\PRSv5\taKeeper.exe"
    DEFAULT_DEBUG_PORT = 9222
    ENV_VAR_NAME = "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"

    def __init__(self, exe_path: str = DEFAULT_EXE_PATH, debug_port: int = DEFAULT_DEBUG_PORT):
        self.exe_path = exe_path
        self.debug_port = debug_port
        self.process: Optional[subprocess.Popen] = None
        self._playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._env_set_in_user_reg = False

    def _set_user_environment_variable(self, port: int):
        """
        UAC 권한 상승으로 실행될 때도 환경 변수를 물려받을 수 있도록
        HKCU\\Environment에 디버깅 포트 인자를 임시 등록합니다.
        """
        val = f"--remote-debugging-port={port}"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, self.ENV_VAR_NAME, 0, winreg.REG_SZ, val)
                self._env_set_in_user_reg = True
        except Exception as e:
            print(f"[경고] 사용자 환경변수 등록 실패: {e}")

    def _clear_user_environment_variable(self):
        """임시 등록한 사용자 환경변수를 제거합니다."""
        if not self._env_set_in_user_reg:
            return
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_SET_VALUE) as key:
                try:
                    winreg.DeleteValue(key, self.ENV_VAR_NAME)
                except FileNotFoundError:
                    pass
        except Exception:
            pass
        self._env_set_in_user_reg = False

    def launch(self, timeout: int = 25):
        """
        taKeeper.exe를 원격 디버깅 모드로 실행하고 Playwright로 연결합니다.
        """
        # 1. 환경 변수 설정
        debug_arg = f"--remote-debugging-port={self.debug_port}"
        os.environ[self.ENV_VAR_NAME] = debug_arg
        self._set_user_environment_variable(self.debug_port)

        working_dir = os.path.dirname(self.exe_path)

        # 2. 프로세스 실행 (일반 실행 실패 시 UAC RunAs 시도)
        try:
            self.process = subprocess.Popen(
                [self.exe_path],
                cwd=working_dir,
                env=os.environ.copy()
            )
        except OSError as e:
            if getattr(e, "winerror", None) == 740:  # Elevation required
                print(">>> 관리자 권한 상승(UAC)으로 taKeeper.exe를 실행합니다...")
                import ctypes
                ret = ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", self.exe_path, "", working_dir, 1
                )
                if ret <= 32:
                    raise RuntimeError(f"관리자 권한 실행 실패 (오류 코드: {ret})")
            else:
                raise

        # 3. CDP 엔드포인트 대기
        print(f">>> WebView2 디버깅 포트({self.debug_port}) 응답 대기 중...")
        self._wait_for_cdp(timeout=timeout)

        # 4. Playwright CDP 연결
        print(">>> Playwright CDP 연결 시도 중...")
        self._connect_playwright()
        print(">>> Playwright 연결 성공!")

    def _wait_for_cdp(self, timeout: int = 25):
        url = f"http://127.0.0.1:{self.debug_port}/json/version"
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                resp = requests.get(url, timeout=1)
                if resp.status_code == 200:
                    return
            except requests.RequestException:
                time.sleep(0.5)
        raise TimeoutError(f"WebView2 CDP 포트({self.debug_port}) 연결 대기 시간({timeout}초) 초과")

    def _connect_playwright(self):
        self._playwright = sync_playwright().start()
        cdp_url = f"http://localhost:{self.debug_port}"
        self.browser = self._playwright.chromium.connect_over_cdp(cdp_url)
        
        # 열린 컨텍스트 확인
        contexts = self.browser.contexts
        if not contexts:
            raise RuntimeError("CDP 브라우저 컨텍스트를 찾을 수 없습니다.")
        self.context = contexts[0]

        # 페이지가 뜰 때까지 잠시 대기
        time.sleep(1)
        pages = self.context.pages
        if pages:
            self.page = pages[0]
        else:
            self.page = self.context.wait_for_event("page", timeout=10000)

    def close(self):
        """정리 및 종료"""
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass

        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass

        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass
            self.process = None

        self._clear_user_environment_variable()
