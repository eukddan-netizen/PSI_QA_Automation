"""
taKeeper.exe 실행/연결 후 WebView2 DOM 구조 및 버튼 요소를 탐색하는 진단 스크립트
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.app_controller import AppController


def main():
    controller = AppController(debug_port=9333)
    try:
        controller.connect(timeout=5)
        page = controller.page
        print(f"\n[성공] taKeeper WebView2 연결 성공!")
        print(f"- 현재 URL: {page.url}")
        print(f"- 페이지 타이틀: {page.title()}")

        # 1. 페이지 내부의 모든 버튼 및 상호작용 요소 수집
        print("\n=== 발견된 버튼 및 상호작용 요소 ===")
        elements = page.locator("button, a, input[type='button'], input[type='submit'], [role='button'], div[onclick]").all()
        for idx, el in enumerate(elements):
            try:
                text = el.inner_text().strip().replace("\n", " ")
                el_id = el.get_attribute("id") or ""
                el_class = el.get_attribute("class") or ""
                print(f"[{idx:02d}] 텍스트: '{text}' | id: '{el_id}' | class: '{el_class}'")
            except Exception:
                pass

        # 2. 메인 페이지 HTML 스냅샷 저장
        snapshot_path = "reports/webview_snapshot.html"
        os.makedirs("reports", exist_ok=True)
        with open(snapshot_path, "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"\n>>> DOM 스냅샷 저장 완료: {snapshot_path}")

        # 3. 화면 스크린샷 저장
        screenshot_path = "reports/webview_screenshot.png"
        page.screenshot(path=screenshot_path)
        print(f">>> 화면 캡처 저장 완료: {screenshot_path}")

    except Exception as e:
        print(f"\n{e}")
    finally:
        print("\n>>> 진단 종료")
        controller.close()


if __name__ == "__main__":
    main()
