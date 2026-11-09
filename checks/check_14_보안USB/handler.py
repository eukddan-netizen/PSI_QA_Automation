"""
14. 보안 USB 설치 여부 점검 전용 OS 핸들러
- 점검 대상: C:\\wwcnt 폴더 존재 여부 (SafeUSB 파일/폴더 존재 판정)
  * C:\\wwcnt 존재 시: 안전
  * C:\\wwcnt 미존재 시: 취약 -> '조치' 클릭 시 스텔스로 C:\\wwcnt 폴더 자동 생성
"""

import shutil
from pathlib import Path
from typing import Tuple
from common.os_utils import StateGuard

TARGET_DIR = Path(r"C:\wwcnt")
BACKUP_DIR = Path(r"C:\wwcnt_psi_backup")


def set_vulnerable(guard: StateGuard) -> None:
    """
    기존 C:\\wwcnt 폴더가 존재하면 C:\\wwcnt_psi_backup으로 안전하게 이동(백업)하여
    C:\\wwcnt가 없는 취약 상태를 만듭니다. 테스트 종료 시 원래 폴더를 복구합니다.
    """
    had_original = TARGET_DIR.exists()
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR, ignore_errors=True)

    if had_original:
        TARGET_DIR.rename(BACKUP_DIR)

    def _restore() -> None:
        if had_original:
            if BACKUP_DIR.exists():
                if TARGET_DIR.exists():
                    shutil.rmtree(TARGET_DIR, ignore_errors=True)
                BACKUP_DIR.rename(TARGET_DIR)
            elif not TARGET_DIR.exists():
                TARGET_DIR.mkdir(parents=True, exist_ok=True)
        else:
            if TARGET_DIR.exists():
                shutil.rmtree(TARGET_DIR, ignore_errors=True)

    guard.add_restore(f"C:\\wwcnt 폴더 원복 (원래 존재여부={had_original})", _restore)


def set_secure(guard: StateGuard) -> None:
    """C:\\wwcnt 폴더가 존재하도록 복원 또는 생성합니다."""
    if BACKUP_DIR.exists() and not TARGET_DIR.exists():
        shutil.copytree(BACKUP_DIR, TARGET_DIR)
    else:
        TARGET_DIR.mkdir(parents=True, exist_ok=True)


def is_secure() -> Tuple[bool, str]:
    """현재 C:\\wwcnt 폴더가 존재하는지 검증합니다."""
    exists = TARGET_DIR.exists() and TARGET_DIR.is_dir()
    if exists:
        return True, "안전 (C:\\wwcnt 보안 USB 폴더 존재함)"
    return False, "취약 (C:\\wwcnt 보안 USB 폴더 존재하지 않음)"

