"""
내 PC 정리 기능 및 실제 파일 삭제 검증 테스트 (Row 51~58)
1. 체크박스 계층 선택/해제 동작 검증 (전체 / Windows / 웹 브라우저)
2. 윈도우 임시 파일(%TEMP%) 정리 및 실제 삭제 검증
3. 휴지통 비우기 실행 및 실제 휴지통 비워짐 검증
4. 웹 브라우저 6개 항목 정리 검증:
   - Chrome > Edge 순서, 브라우저별 Default > Profile 1 > Profile 2 순서
   - 브라우저 자동 종료 없음 / 삭제 실패 시 오류 미표시
   - 참고: 현재 Edge의 '기록 및 탐색 데이터' 정리 미동작 이슈는 xfail 처리
"""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Dict, List, Tuple

import pytest

from core.app_controller import AppController
from pages.client.clean_page import CleanPage


BROWSER_BASE_DIRS: List[Tuple[str, str, Path]] = [
    ("Chrome", "chrome.exe", Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"),
    ("Edge", "msedge.exe", Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data"),
]

PROFILE_ORDER = ["Default", "Profile 1", "Profile 2"]

# <화면 항목: 삭제할 파일·폴더> (폴더와 파일을 구분하여 더미 생성 시 활용)
BROWSER_CLEAN_TARGETS: Dict[str, List[Tuple[str, str]]] = {
    "캐시 및 성능 데이터": [
        ("Cache", "dir"),
        ("Code Cache", "dir"),
        ("GPUCache", "dir"),
    ],
    "기록 및 탐색 데이터": [
        ("History", "file"),
        ("Top Sites", "file"),
        ("Visited Links", "file"),
        ("Network Action Predictor", "file"),
    ],
    "저장소 데이터": [
        (r"Local Storage\leveldb", "dir"),
        ("Session Storage", "dir"),
        (r"Storage\ext", "dir"),
    ],
    "세션 및 사용자 설정": [
        ("Sessions", "dir"),
        ("Shortcuts", "file"),
        ("Extension State", "dir"),
    ],
    "쿠키 및 사용자 인증 데이터": [
        ("Cookies", "file"),
        ("Cookies-journal", "file"),
        ("Web Data", "file"),
    ],
    "미디어 데이터": [
        ("Media Cache", "dir"),
    ],
}


class _SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("i64Size", ctypes.c_int64),
        ("i64NumItems", ctypes.c_int64),
    ]


class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_uint16),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def _get_recycle_bin_count() -> int:
    """Windows 휴지통 내 항목 개수 반환"""
    info = _SHQUERYRBINFO()
    info.cbSize = ctypes.sizeof(_SHQUERYRBINFO)
    hr = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
    if hr != 0:
        raise OSError(f"SHQueryRecycleBinW 실패: HRESULT={hr}")
    return int(info.i64NumItems)


def _send_to_recycle_bin(file_path: Path) -> None:
    """지정된 파일을 Windows 휴지통으로 이동"""
    FO_DELETE = 3
    FOF_SILENT = 0x0004
    FOF_NOCONFIRMATION = 0x0010
    FOF_ALLOWUNDO = 0x0040

    op = _SHFILEOPSTRUCTW()
    op.wFunc = FO_DELETE
    op.pFrom = str(file_path) + "\0\0"
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if rc != 0 or op.fAnyOperationsAborted:
        raise OSError(f"휴지통 이동 실패: rc={rc}, aborted={op.fAnyOperationsAborted}")


def _is_process_running(exe_name: str) -> bool:
    """지정된 프로세스(예: chrome.exe, msedge.exe)가 현재 실행 중인지 확인"""
    res = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/NH"],
        capture_output=True,
        text=True,
        encoding="cp949",
        errors="replace",
    )
    return exe_name.lower() in (res.stdout or "").lower()


def _is_file_locked(file_path: Path) -> bool:
    """Windows CreateFileW 배타적 열기(dwShareMode=0)로 파일이 OS/다른 프로세스에 의해 잠겼는지 확인"""
    GENERIC_READ = 0x80000000
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
    LOCK_ERROR_CODES = {5, 32, 33}  # ACCESS_DENIED, SHARING_VIOLATION, LOCK_VIOLATION

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.restype = wintypes.HANDLE
    handle = kernel32.CreateFileW(
        str(file_path),
        GENERIC_READ,
        0,  # 공유 모드 없음 -> 다른 프로세스가 사용 중이면 실패
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        return ctypes.get_last_error() in LOCK_ERROR_CODES
    kernel32.CloseHandle(handle)
    return False


def _is_path_locked(target_path: Path) -> bool:
    """파일 또는 폴더(내부 파일 포함)가 현재 OS 잠금 상태인지 확인"""
    if not target_path.exists():
        return False
    if target_path.is_file():
        return _is_file_locked(target_path)
    try:
        for child in target_path.rglob("*"):
            if child.is_file() and _is_file_locked(child):
                return True
    except PermissionError:
        return True
    return False


def _create_dummy_target(target_path: Path, kind: str) -> None:
    """테스트용 더미 파일 또는 폴더(내부 더미 파일 포함)를 생성"""
    if kind == "dir":
        target_path.mkdir(parents=True, exist_ok=True)
        (target_path / "psi_clean_dummy.tmp").write_text("dummy", encoding="utf-8")
    else:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text("dummy", encoding="utf-8")


def _cleanup_path(target_path: Path) -> None:
    """테스트 종료 시 남아있는 더미 파일/폴더 정리"""
    try:
        if target_path.is_dir():
            shutil.rmtree(target_path, ignore_errors=True)
        elif target_path.exists():
            target_path.unlink(missing_ok=True)
    except Exception:
        pass


def _print_section_header(title: str) -> None:
    print(f"\n==================== [{title}] ====================")


def _print_section_footer(title: str) -> None:
    print(f"==================== [{title} 끝] ====================")


@pytest.fixture(scope="module")
def clean_page():
    """모듈 내 테스트 동안 보안점검 프로그램을 1회만 실행하고 'PC정리' 탭을 재사용"""
    ctrl = AppController()
    ctrl.launch(timeout=30)
    page = CleanPage(ctrl.hwnd)
    page.wait_for_main_ready(timeout=15)
    page.navigate_to_tab("PC정리", timeout=10)
    page.wait_for_clean_ready(timeout=10)
    yield page
    try:
        ctrl.close()
    except Exception:
        pass


@pytest.mark.app_check
@pytest.mark.app_clean
def test_010_PC정리_트리체크박스_일괄선택해제(clean_page: CleanPage):
    """
    [APP-06-02-010] PC정리 트리 체크박스(전체·Windows·브라우저) 일괄 선택/해제 검증
    """
    title = "체크박스 계층 선택·해제"
    _print_section_header(title)
    try:
        clean_page.uncheck_all()
        for item in CleanPage.ALL_LEAF_ITEMS:
            assert clean_page.get_checkbox_state(item) == 0, f"초기화 후 '{item}'이 해제되지 않았습니다."

        # 'Windows' 상위 체크박스 선택 -> 하위 2개 선택 확인
        clean_page.set_checkbox("Windows", True)
        for item in CleanPage.WINDOWS_ITEMS:
            assert clean_page.get_checkbox_state(item) == 1, f"'Windows' 선택 후 '{item}'이 선택되지 않았습니다."
        for item in CleanPage.BROWSER_ITEMS:
            assert clean_page.get_checkbox_state(item) == 0, f"'Windows' 선택 시 '{item}'은 해제 상태여야 합니다."

        # '웹 브라우저' 상위 체크박스 선택 -> 하위 6개 선택 및 '전체' 선택 확인
        clean_page.set_checkbox("웹 브라우저", True)
        for item in CleanPage.BROWSER_ITEMS:
            assert clean_page.get_checkbox_state(item) == 1, f"'웹 브라우저' 선택 후 '{item}'이 선택되지 않았습니다."
        assert clean_page.get_checkbox_state("전체") == 1, "모든 하위 항목 선택 시 '전체'도 선택 상태여야 합니다."

        # '전체' 해제 -> 전체 항목 해제 확인
        clean_page.set_checkbox("전체", False)
        for item in CleanPage.ALL_LEAF_ITEMS:
            assert clean_page.get_checkbox_state(item) == 0, f"'전체' 해제 후 '{item}'이 해제되지 않았습니다."
        print(">>> [결과] 전체 / Windows / 웹 브라우저 계층 선택·해제 정상")
    finally:
        _print_section_footer(title)


@pytest.mark.app_check
@pytest.mark.app_clean
def test_020_윈도우_임시파일_정리_삭제검증(clean_page: CleanPage):
    """
    [APP-06-02-020] 더미 임시파일 생성 후 윈도우 임시 파일 정리 실제 삭제 검증
    """
    title = "윈도우 임시 파일"
    temp_dir = Path(os.environ["TEMP"])
    dummy_file = temp_dir / f"psi_clean_temp_dummy_{int(time.time())}.tmp"
    dummy_file.write_text("psi temp clean test", encoding="utf-8")
    assert dummy_file.exists(), "테스트용 임시 더미 파일 생성에 실패했습니다."

    _print_section_header(title)
    try:
        print(f">>> [정리 전] 더미 파일: {dummy_file} (존재={dummy_file.exists()})")
        clean_page.run_clean_for_items(["윈도우 임시 파일"], timeout=15.0)
        exists_after = dummy_file.exists()
        print(f">>> [정리 후] 결과: {'삭제됨' if not exists_after else '미삭제'} ({dummy_file})")
        assert not exists_after, f"윈도우 임시 파일 정리 후 더미 파일이 삭제되지 않았습니다: {dummy_file}"
    finally:
        if dummy_file.exists():
            dummy_file.unlink(missing_ok=True)
        _print_section_footer(title)


@pytest.mark.app_check
@pytest.mark.app_clean
def test_030_휴지통_비우기_실행_삭제검증(clean_page: CleanPage):
    """
    [APP-06-02-030] 휴지통 비우기 실행 후 완료 팝업 및 실제 비워짐 검증
    """
    title = "휴지통 비우기"
    temp_dir = Path(os.environ["TEMP"])
    dummy_file = temp_dir / f"psi_clean_rb_dummy_{int(time.time())}.tmp"
    dummy_file.write_text("psi recycle bin clean test", encoding="utf-8")

    _print_section_header(title)
    try:
        _send_to_recycle_bin(dummy_file)
        before_count = _get_recycle_bin_count()
        print(f">>> [정리 전] 휴지통 항목 수: {before_count}")
        assert before_count >= 1, "테스트용 파일을 휴지통으로 이동했으나 휴지통 항목 수가 0입니다."

        clean_page.run_clean_for_items(["휴지통 비우기"], timeout=15.0)
        after_count = _get_recycle_bin_count()
        print(f">>> [정리 후] 휴지통 항목 수: {after_count}")
        assert after_count == 0, f"휴지통 비우기 후에도 휴지통에 {after_count}개 항목이 남아 있습니다."
    finally:
        if dummy_file.exists():
            dummy_file.unlink(missing_ok=True)
        _print_section_footer(title)


@pytest.mark.app_check
@pytest.mark.app_clean
@pytest.mark.parametrize("category", list(BROWSER_CLEAN_TARGETS.keys()))
def test_040_웹브라우저_항목별_정리검증(clean_page: CleanPage, category: str):
    """
    [APP-06-02-040] 웹 브라우저(Chrome·Edge) 항목별 캐시·쿠키 정리 검증
    - Chrome > Edge 순서, Default > Profile 1 > Profile 2 순서로 존재하는 프로필 대상 확인
    - 미존재 경로는 테스트용 더미 생성 후 삭제 여부 검증
    - 브라우저가 실행 중인 경우 OS 잠금 파일은 제외하고 오류 팝업 없이 완료되는지 검증
    """
    targets = BROWSER_CLEAN_TARGETS[category]

    # 존재하는 브라우저 프로필 탐색 (Chrome > Edge, Default > Profile 1 > Profile 2)
    existing_profiles: List[Tuple[str, str, str, Path]] = []
    for browser_name, exe_name, user_data_dir in BROWSER_BASE_DIRS:
        if not user_data_dir.exists():
            continue
        for profile_name in PROFILE_ORDER:
            profile_dir = user_data_dir / profile_name
            if profile_dir.exists():
                existing_profiles.append((browser_name, exe_name, profile_name, profile_dir))

    if not existing_profiles:
        pytest.skip("Chrome/Edge 사용자 프로필(Default, Profile 1, Profile 2)이 존재하지 않습니다.")

    title = f"웹 브라우저 - {category}"
    created_dummies: List[Path] = []
    watched_targets: List[Tuple[str, str, str, Path, bool]] = []

    _print_section_header(title)
    try:
        for browser_name, exe_name, profile_name, profile_dir in existing_profiles:
            for rel_path, kind in targets:
                t_path = profile_dir / rel_path
                is_dummy = False
                if not t_path.exists():
                    _create_dummy_target(t_path, kind)
                    created_dummies.append(t_path)
                    is_dummy = True
                watched_targets.append((browser_name, exe_name, profile_name, t_path, is_dummy))

        print(">>> [탐색된 프로필] " + ", ".join(f"{b}/{p}" for b, _, p, _ in existing_profiles))
        print(f">>> [정리 전] 대상 목록 ({len(watched_targets)}건):")
        for browser_name, _exe_name, profile_name, t_path, is_dummy in watched_targets:
            origin = "더미 생성" if is_dummy else "기존 파일"
            print(f"    - [{browser_name}/{profile_name}] ({origin}) {t_path}")

        clean_page.run_clean_for_items([category], timeout=20.0)

        chrome_failures: List[str] = []
        edge_failures: List[str] = []
        deleted_count = 0
        locked_count = 0

        print(">>> [정리 후] 결과:")
        for browser_name, exe_name, profile_name, t_path, is_dummy in watched_targets:
            still_exists = t_path.exists()
            if not still_exists:
                deleted_count += 1
                print(f"    - [삭제됨] [{browser_name}/{profile_name}] {t_path}")
                continue

            browser_running = _is_process_running(exe_name)
            path_locked = _is_path_locked(t_path)
            if browser_running and not is_dummy and path_locked:
                locked_count += 1
                print(
                    f"    - [미삭제 - {exe_name} 실행 중 OS 잠금 확인됨] "
                    f"[{browser_name}/{profile_name}] {t_path}"
                )
                continue

            reason = f"미삭제 - 실패({exe_name} 실행 중이나 파일 잠금 아님)" if browser_running else "미삭제 - 실패"
            print(f"    - [{reason}] [{browser_name}/{profile_name}] {t_path}")
            msg = f"[{browser_name} / {profile_name}] {t_path}"
            if browser_name == "Chrome":
                chrome_failures.append(msg)
            else:
                edge_failures.append(msg)

        fail_count = len(chrome_failures) + len(edge_failures)
        print(
            f">>> [요약] 총 {len(watched_targets)}건 | "
            f"삭제 {deleted_count}건 | 실행 중 잠금 제외 {locked_count}건 | 미삭제 실패 {fail_count}건"
        )

        assert not chrome_failures, (
            f"'{category}' 정리 후 Chrome 대상 파일/폴더가 삭제되지 않았습니다:\n" + "\n".join(chrome_failures)
        )

        if edge_failures:
            if category == "기록 및 탐색 데이터":
                pytest.xfail(
                    "현재 Edge에서 '기록 및 탐색 데이터' 정리 기능이 동작하지 않는 알려진 이슈: "
                    + ", ".join(edge_failures)
                )
            pytest.fail(
                f"'{category}' 정리 후 Edge 대상 파일/폴더가 삭제되지 않았습니다:\n" + "\n".join(edge_failures)
            )
    finally:
        for dummy_path in created_dummies:
            _cleanup_path(dummy_path)
        _print_section_footer(title)
