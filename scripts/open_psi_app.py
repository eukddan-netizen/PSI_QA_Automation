"""
AppController를 이용해 사용자 모니터에 보안점검 창을 자동으로 실행/표시하는 스크립트
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.app_controller import AppController


def main():
    print(">>> [AppController] 보안점검 창 자동 실행 시작...")
    controller = AppController()
    try:
        win = controller.launch(timeout=10)
        print(f"\n>>> [성공!] 보안점검 창이 모니터 화면에 정상적으로 표시되었습니다!")
        print(f"- 창 타이틀: {win.window_text()}")
        print(f"- 화면 위치/크기: {win.rectangle()}")
    except Exception as e:
        print(f"\n>>> [실행 실패] {e}")


if __name__ == "__main__":
    main()
