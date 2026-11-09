"""
taKeeper.exe 실행 후 WebView2 DOM 구조 및 버튼 요소를 탐색하는 진단 스크립트
"""

import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.app_controller import AppController


def main():
    print(">>> taKeeper.exe 실행 및 WebView2 CDP 연결 시도...")
    controller = AppController()
    try:
        controller.launch(timeout=20)
        page = controller.page
        print(f">>> 연결 성공! 현재 페이지 URL: {page.url}")
        print(f">>> 페이지 타이틀: {page.title()}")

        # 1. 페이지 내부의 모든 버튼과 텍스트 수집
        print("\n=== 발견된 버튼 목록 ===")
        buttons = page.locator("button, a, input[type='button'], input[type='submit']").all()
        for idx, btn in enumerate(buttons):
            try:
                text = btn.inner_text().strip()
                btn_id = btn.get_attribute("id") or ""
                btn_class = btn.get_attribute("class") or ""
                print(f"[{idx}] text='{text}' | id='{btn_id}' | class='{btn_class}'")
            except Exception as e:
                pass

        # 2. 메인 페이지 HTML 스냅샷 저장
        snapshot_path = "reports/webview_snapshot.html"
        os.makedirs("reports", exist_ok=True)
        with open(snapshot_path, "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"\n>>> DOM 스냅샷이 저장되었습니다: {snapshot_path}")

        # 3. 화면 스크린샷 저장
        screenshot_path = "reports/webview_screenshot.png"
        page.screenshot(path=screenshot_path)
        print(f">>> 화면 캡처가 저장되었습니다: {screenshot_path}")

    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        print("\n>>> 5초 후 프로그램을 정리합니다...")
        import time
        time.sleep(5)
        controller.close()


if __name__ == "__main__":
    main()
