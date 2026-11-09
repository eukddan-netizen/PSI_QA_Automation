"""
taKeeper.exe (보안점검 프로그램) 제어 및 WebView2 CDP 연결 컨트롤러
"""

import os
import sys
import time
import requests
import subprocess
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page


class AppController:
    DEFAULT_EXE_PATH = r"C:\Program Files (x86)\topaegis\PRSv5\taKeeper.exe"
    DEFAULT_DEBUG_PORT = 9333  # Teams 등 다른 WebView2 앱과의 충돌을 피하기 위해 9333 포트 사용

    def __init__(self, exe_path: str = DEFAULT_EXE_PATH, debug_port: int = DEFAULT_DEBUG_PORT):
        self.exe_path = exe_path
        self.debug_port = debug_port
        self.process: Optional[subprocess.Popen] = None
        self._playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def is_cdp_ready(self) -> bool:
        """지정된 포트에서 WebView2 CDP가 응답하는지 확인합니다."""
        url = f"http://127.0.0.1:{self.debug_port}/json/version"
        try:
            resp = requests.get(url, timeout=1)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def connect(self, timeout: int = 10):
        """
        포트(9333)로 열려 있는 taKeeper WebView2 세션에 Playwright로 연결합니다.
        """
        print(f">>> 포트({self.debug_port})에서 taKeeper WebView2 연결 대기 중...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_cdp_ready():
                print(f">>> 포트({self.debug_port}) 응답 확인! Playwright로 연결합니다...")
                self._connect_playwright()
                return
            time.sleep(1)

        raise TimeoutError(
            f"\n[연결 실패] 포트 {self.debug_port}에서 응답이 없습니다.\n"
            f"👉 먼저 'd:\\psi_automation\\start_app_debug.bat' 파일을 실행하여\n"
            f"   taKeeper를 디버그 모드로 띄운 후 다시 시도해 주세요!"
        )

    def _connect_playwright(self):
        self._playwright = sync_playwright().start()
        cdp_url = f"http://localhost:{self.debug_port}"
        self.browser = self._playwright.chromium.connect_over_cdp(cdp_url)
        
        contexts = self.browser.contexts
        if not contexts:
            raise RuntimeError("CDP 브라우저 컨텍스트를 찾을 수 없습니다.")
        self.context = contexts[0]

        # 점검창 페이지 찾기
        for _ in range(10):
            pages = self.context.pages
            if pages:
                # about:blank가 아닌 실제 페이지 선호
                for p in pages:
                    if "about:blank" not in p.url:
                        self.page = p
                        return
                self.page = pages[0]
                return
            time.sleep(0.5)
            
        self.page = self.context.wait_for_event("page", timeout=5000)

    def close(self):
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
