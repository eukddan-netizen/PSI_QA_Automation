"""
내 PC 정리 기능 및 실제 데이터/DB 삭제 검증 테스트 (개편 스펙 반영)
1. 신규 안내 문구 및 트리 체크박스 계층 선택/해제 검증
   - Windows(2): 윈도우 임시 파일, 휴지통 비우기
   - 웹 브라우저(5): 방문 기록, 다운로드 기록, 쿠키 및 기타 사이트 데이터, 캐시된 이미지 및 파일, 자동 완성 양식 데이터
   - 구 항목(미디어 데이터, 캐시 및 성능 데이터 등) 미노출 확인
2. 윈도우 임시 파일(%TEMP%) 정리 및 실제 삭제 검증
3. 휴지통 비우기 실행 및 실제 휴지통 비워짐 검증
4. 확인 모달 프로필 선택 UI 검증:
   - Chrome/Edge별 'Default', 'Profile N' 프로필명(폴더명) 표시 및 기본 미선택 확인
   - 프로필 미선택 시 안내 문구 노출 및 '정리하기' 버튼 비활성화 확인
   - 특정 프로필 선택 시 '정리하기' 활성화 및 미선택 프로필 데이터 보존 검증
5. 웹 브라우저 5개 항목별 DB·저장소 선택 정리 및 보존 데이터(북마크/타 항목/미선택 프로필) 검증
6. 실행 중인 브라우저 자동 종료 안내 및 실제 프로세스 종료 + 정리 완료 검증
"""

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest
import win32gui
import win32process

from core.app_controller import AppController
from core.desktop_utils import switch_to_user_desktop
from pages.client.clean_page import CleanPage


SELECTED_TEST_PROFILE = "Profile 99"
UNSELECTED_TEST_PROFILE = "Profile 98"

BROWSER_SPECS: List[Dict[str, Any]] = [
    {
        "name": "Chrome",
        "exe_name": "chrome.exe",
        "exe_candidates": [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path(os.environ.get("LOCALAPPDATA", "")) / r"Google\Chrome\Application\chrome.exe",
        ],
        "user_data_dir": Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data",
    },
    {
        "name": "Edge",
        "exe_name": "msedge.exe",
        "exe_candidates": [
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            Path(os.environ.get("LOCALAPPDATA", "")) / r"Microsoft\Edge\Application\msedge.exe",
        ],
        "user_data_dir": Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data",
    },
]

DEPRECATED_BROWSER_ITEMS = [
    "캐시 및 성능 데이터",
    "기록 및 탐색 데이터",
    "저장소 데이터",
    "세션 및 사용자 설정",
    "쿠키 및 사용자 인증 데이터",
    "미디어 데이터",
]


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


def _kill_process(exe_name: str) -> None:
    subprocess.run(["taskkill", "/F", "/IM", exe_name], capture_output=True)
    deadline = time.time() + 5.0
    while time.time() < deadline and _is_process_running(exe_name):
        time.sleep(0.2)


def _kill_pid_tree(pid: int) -> None:
    """특정 PID와 그 하위 프로세스만 종료 (기존 사용자의 브라우저 창에 영향 없음)"""
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)


def _get_hwnd_exe_name(hwnd: int) -> str:
    """윈도우 핸들을 소유한 프로세스의 실행 파일명(소문자, 예: 'chrome.exe') 반환"""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return ""
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        k32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        k32.CloseHandle.restype = wintypes.BOOL

        h_proc = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h_proc:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(512)
            size = wintypes.DWORD(len(buf))
            ok = k32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size))
            return Path(buf.value).name.lower() if ok and buf.value else ""
        finally:
            k32.CloseHandle(h_proc)
    except Exception:
        return ""


def _detect_protected_dashboard_browsers() -> Set[str]:
    """
    QA 대시보드('PSI QA Automation Monitor')를 띄우고 있는 브라우저 이름('Chrome' / 'Edge')을 탐지합니다.
    taKeeper.exe는 정리 대상으로 선택된 브라우저의 모든 창/프로세스를 종료하므로,
    대시보드를 보고 있는 브라우저가 테스트 중 강제 종료되지 않도록 보호하는 데 사용합니다.
    """
    switch_to_user_desktop()
    exe_to_name = {spec["exe_name"].lower(): spec["name"] for spec in BROWSER_SPECS}
    protected: Set[str] = set()
    visible_browser_exes: Set[str] = set()

    def _cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        exe = _get_hwnd_exe_name(hwnd)
        if exe not in exe_to_name:
            return
        visible_browser_exes.add(exe)
        title = win32gui.GetWindowText(hwnd) or ""
        if any(k in title for k in ("PSI QA", "127.0.0.1:8000", "localhost:8000")):
            protected.add(exe_to_name[exe])

    win32gui.EnumWindows(_cb, None)

    # 대시보드에서 실행된 런(PSI_DASHBOARD_RUN_ID)인데 사용자가 다른 탭을 보고 있어
    # 창 제목에 'PSI QA'가 보이지 않는 경우, 단독으로 떠 있는 브라우저 1종을 대시보드 브라우저로 보호
    if not protected and os.environ.get("PSI_DASHBOARD_RUN_ID"):
        if len(visible_browser_exes) == 1:
            only_exe = next(iter(visible_browser_exes))
            protected.add(exe_to_name[only_exe])

    return protected


def _find_browser_exe(spec: Dict[str, Any]) -> Optional[Path]:
    for cand in spec["exe_candidates"]:
        if cand.exists():
            return cand
    return None


def _insert_dummy_row(cur: sqlite3.Cursor, table: str, overrides: Dict[str, Any]) -> None:
    """PRAGMA table_info로 실제 Chromium 테이블 컬럼을 조회해 NOT NULL 제약을 만족하는 더미 행 1건 삽입"""
    info = cur.execute(f"PRAGMA table_info({table})").fetchall()
    if not info:
        return
    cols = [r[1] for r in info]
    vals = []
    for _cid, name, typ, _nn, _df, _pk in info:
        if name in overrides:
            vals.append(overrides[name])
        elif "INT" in typ.upper():
            vals.append(13380000000000000 if ("utc" in name or "time" in name) else 0)
        elif "BLOB" in typ.upper():
            vals.append(b"")
        else:
            vals.append("")
    placeholders = ",".join("?" for _ in cols)
    cur.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})", vals)


def _copy_file_shared(src: Path, dst: Path) -> bool:
    """다른 프로세스(실행 중인 브라우저 등)가 열고 있는 파일도 공유 읽기 모드로 안전하게 복사합니다."""
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(src, dst)
        return True
    except PermissionError:
        pass

    # Windows CreateFileW(FILE_SHARE_READ|WRITE|DELETE)로 잠금 상태 DB 읽기 복사
    GENERIC_READ = 0x80000000
    FILE_SHARE_ALL = 0x00000001 | 0x00000002 | 0x00000004
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.ReadFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    k32.ReadFile.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL

    h = k32.CreateFileW(str(src), GENERIC_READ, FILE_SHARE_ALL, None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)
    if h == INVALID_HANDLE_VALUE:
        return False
    try:
        buf = ctypes.create_string_buffer(65536)
        bytes_read = wintypes.DWORD(0)
        with dst.open("wb") as fp:
            while k32.ReadFile(h, buf, len(buf), ctypes.byref(bytes_read), None) and bytes_read.value > 0:
                fp.write(buf.raw[: bytes_read.value])
        return dst.exists() and dst.stat().st_size > 0
    except Exception:
        return False
    finally:
        k32.CloseHandle(h)


def _seed_profile_data(profile_dir: Path, template_dir: Path, fallback_default_dir: Path) -> None:
    """
    Chromium SQLite 스키마 템플릿을 복사한 뒤,
    5개 정리 항목의 DB 레코드·캐시 파일과 보존 검증용 북마크를 시드합니다.
    """
    if profile_dir.exists():
        shutil.rmtree(profile_dir, ignore_errors=True)
    shutil.copytree(template_dir, profile_dir, dirs_exist_ok=True)

    # 필수 SQLite DB가 템플릿에 없으면 동일 브라우저 Default 프로필에서 공유 읽기 복제
    for rel in ("History", "Web Data", r"Network\Cookies"):
        target_db = profile_dir / rel
        if not target_db.exists():
            _copy_file_shared(fallback_default_dir / rel, target_db)

    # 보존 검증용 정품 Chromium Bookmarks JSON (방문 기록 정리 시 북마크 보존 파싱 호환)
    valid_bookmarks = {
        "checksum": "",
        "roots": {
            "bookmark_bar": {
                "children": [
                    {
                        "name": "PSI_KEEP",
                        "type": "url",
                        "url": "https://keep.psi-test.example.com/",
                    }
                ],
                "name": "Bookmarks bar",
                "type": "folder",
            },
            "other": {"children": [], "name": "Other bookmarks", "type": "folder"},
            "synced": {"children": [], "name": "Mobile bookmarks", "type": "folder"},
        },
        "version": 1,
    }
    (profile_dir / "Bookmarks").write_text(json.dumps(valid_bookmarks, ensure_ascii=False), encoding="utf-8")

    # 1~2. History DB (방문 기록: urls/visits, 다운로드 기록: downloads/downloads_url_chains)
    hdb = profile_dir / "History"
    if hdb.exists():
        con = sqlite3.connect(hdb)
        cur = con.cursor()
        tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        for t in ("urls", "visits", "downloads", "downloads_url_chains"):
            if t in tables:
                cur.execute(f"DELETE FROM {t}")
        if "urls" in tables:
            _insert_dummy_row(
                cur,
                "urls",
                {"id": 999, "url": "https://psi-clean-test.example.com/", "title": "PSI Clean Test", "visit_count": 1},
            )
        if "visits" in tables:
            _insert_dummy_row(cur, "visits", {"id": 999, "url": 999})
        if "downloads" in tables:
            _insert_dummy_row(
                cur,
                "downloads",
                {
                    "id": 999,
                    "guid": "psi-download-guid-999",
                    "current_path": r"C:\Temp\psi_dummy.txt",
                    "target_path": r"C:\Temp\psi_dummy.txt",
                    "received_bytes": 128,
                    "total_bytes": 128,
                    "state": 1,
                },
            )
        if "downloads_url_chains" in tables:
            _insert_dummy_row(
                cur,
                "downloads_url_chains",
                {"id": 999, "chain_index": 0, "url": "https://psi-clean-test.example.com/psi_dummy.txt"},
            )
        con.commit()
        con.close()

    # 3. 쿠키 DB (Network\Cookies)
    cdb = profile_dir / "Network" / "Cookies"
    if cdb.exists():
        con = sqlite3.connect(cdb)
        cur = con.cursor()
        tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "cookies" in tables:
            cur.execute("DELETE FROM cookies")
            _insert_dummy_row(
                cur,
                "cookies",
                {"host_key": ".psi-clean-test.example.com", "name": "psi_cookie", "value": "1", "path": "/"},
            )
        con.commit()
        con.close()

    # 4. 캐시된 이미지 및 파일 (Cache\Cache_Data, Code Cache)
    (profile_dir / "Cache" / "Cache_Data").mkdir(parents=True, exist_ok=True)
    (profile_dir / "Cache" / "Cache_Data" / "f_psi_dummy").write_bytes(b"psi_cache_dummy_bytes")
    (profile_dir / "Code Cache" / "js").mkdir(parents=True, exist_ok=True)
    (profile_dir / "Code Cache" / "js" / "psi_dummy.bin").write_bytes(b"psi_code_cache_dummy")

    # 5. 자동 완성 양식 데이터 (Web Data.autofill)
    wdb = profile_dir / "Web Data"
    if wdb.exists():
        con = sqlite3.connect(wdb)
        cur = con.cursor()
        tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "autofill" in tables:
            cur.execute("DELETE FROM autofill")
            _insert_dummy_row(
                cur,
                "autofill",
                {"name": "psi_field", "value": "psi_value", "value_lower": "psi_value", "count": 1},
            )
        con.commit()
        con.close()


def _snapshot_profile(profile_dir: Path) -> Dict[str, Any]:
    """프로필 내 5개 항목 데이터 상태 및 북마크 보존 여부를 스냅샷으로 반환"""
    snap: Dict[str, Any] = {
        "bookmarks_exists": (profile_dir / "Bookmarks").exists(),
        "cache_data_exists": (profile_dir / "Cache" / "Cache_Data" / "f_psi_dummy").exists(),
        "code_cache_exists": (profile_dir / "Code Cache" / "js" / "psi_dummy.bin").exists(),
    }

    hdb = profile_dir / "History"
    if hdb.exists():
        con = sqlite3.connect(hdb)
        cur = con.cursor()
        tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        for t in ("urls", "visits", "downloads", "downloads_url_chains"):
            snap[f"history_{t}"] = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if t in tables else None
        con.close()

    cdb = profile_dir / "Network" / "Cookies"
    if cdb.exists():
        con = sqlite3.connect(cdb)
        cur = con.cursor()
        tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        snap["cookies_count"] = cur.execute("SELECT COUNT(*) FROM cookies").fetchone()[0] if "cookies" in tables else None
        con.close()

    wdb = profile_dir / "Web Data"
    if wdb.exists():
        con = sqlite3.connect(wdb)
        cur = con.cursor()
        tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        snap["autofill_count"] = cur.execute("SELECT COUNT(*) FROM autofill").fetchone()[0] if "autofill" in tables else None
        con.close()

    return snap


def _remove_profiles_from_local_state(user_data_dir: Path, profile_names: List[str]) -> None:
    """테스트 종료 시 Local State의 info_cache에서 임시 프로필 항목을 정리"""
    ls = user_data_dir / "Local State"
    if not ls.exists():
        return
    try:
        data = json.loads(ls.read_text(encoding="utf-8"))
        info_cache = data.get("profile", {}).get("info_cache", {})
        changed = False
        for pname in profile_names:
            if pname in info_cache:
                del info_cache[pname]
                changed = True
        if changed:
            ls.write_text(json.dumps(data), encoding="utf-8")
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


@pytest.fixture(scope="module")
def browser_test_env():
    """
    실제 사용자 Default 프로필과 실행 중인 QA 대시보드 브라우저를 훼손하지 않고
    신규 PC정리(프로필 선택·DB 정리·자동 종료)를 검증하기 위해
    격리된 임시 프로필(Profile 99=선택, Profile 98=미선택)을 생성하고 모듈 종료 시 원복합니다.
    (별도 --user-data-dir로 브라우저를 띄우지 않고 기존 Chromium Default DB 스키마를 안전 복제하여
    권한 팝업('데이터 디렉터리 만들기 실패')과 대시보드 창 종료를 원천 방지합니다.)
    """
    tmp_root = Path(tempfile.mkdtemp(prefix="psi_clean_templates_"))
    protected_browsers = _detect_protected_dashboard_browsers()
    if protected_browsers:
        print(f"\n>>> [대시보드 보호] 실행 중인 대시보드 브라우저 감지: {sorted(protected_browsers)}")

    # Chrome/Edge Default 프로필에서 사용 가능한 정품 Chromium SQLite DB 스키마를 수집 (공유 읽기 복사)
    installed_specs: List[Tuple[Dict[str, Any], Path]] = []
    for spec in BROWSER_SPECS:
        exe = _find_browser_exe(spec)
        udir: Path = spec["user_data_dir"]
        if exe and udir.exists():
            installed_specs.append((spec, exe))

    shared_fallback_dbs: Dict[str, Path] = {}
    for rel in ("History", "Web Data", r"Network\Cookies"):
        for spec, _ in installed_specs:
            src = spec["user_data_dir"] / "Default" / rel
            dst = tmp_root / "_shared_fallback" / rel
            if _copy_file_shared(src, dst):
                shared_fallback_dbs[rel] = dst
                break

    has_non_dashboard = any(spec["name"] not in protected_browsers for spec, _ in installed_specs)
    active_browsers: List[Dict[str, Any]] = []

    try:
        for spec, exe in installed_specs:
            udir: Path = spec["user_data_dir"]
            is_dash = spec["name"] in protected_browsers
            default_dir = udir / "Default"
            selected_dir = udir / SELECTED_TEST_PROFILE
            unselected_dir = udir / UNSELECTED_TEST_PROFILE

            # 다른 비대시보드 브라우저가 존재하면 대시보드 브라우저의 User Data는 일절 건드리지 않음
            if is_dash and has_non_dashboard:
                active_browsers.append({
                    "name": spec["name"],
                    "exe_name": spec["exe_name"],
                    "exe_path": exe,
                    "user_data_dir": udir,
                    "default_dir": default_dir,
                    "template_dir": None,
                    "selected_dir": selected_dir,
                    "unselected_dir": unselected_dir,
                    "is_dashboard_browser": True,
                    "has_test_profiles": False,
                })
                continue

            if not is_dash:
                _kill_process(spec["exe_name"])

            for d in (selected_dir, unselected_dir):
                shutil.rmtree(d, ignore_errors=True)

            # 해당 브라우저의 Default DB 스키마를 우선 복제하고, 누락 DB는 동일 Chromium 계열 폴백 사용
            tpl_dir = tmp_root / f"tpl_{spec['name']}"
            tpl_dir.mkdir(parents=True, exist_ok=True)
            for rel in ("History", "Web Data", r"Network\Cookies"):
                dst = tpl_dir / rel
                if not _copy_file_shared(default_dir / rel, dst):
                    fb = shared_fallback_dbs.get(rel)
                    if fb and fb.exists():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(fb, dst)

            # 선택/미선택 프로필 초기 시드
            _seed_profile_data(selected_dir, tpl_dir, default_dir)
            _seed_profile_data(unselected_dir, tpl_dir, default_dir)

            active_browsers.append({
                "name": spec["name"],
                "exe_name": spec["exe_name"],
                "exe_path": exe,
                "user_data_dir": udir,
                "default_dir": default_dir,
                "template_dir": tpl_dir,
                "selected_dir": selected_dir,
                "unselected_dir": unselected_dir,
                "is_dashboard_browser": is_dash,
                "has_test_profiles": True,
            })

        yield active_browsers
    finally:
        for b in active_browsers:
            if not b.get("has_test_profiles"):
                continue
            if not b.get("is_dashboard_browser"):
                _kill_process(b["exe_name"])
            shutil.rmtree(b["selected_dir"], ignore_errors=True)
            shutil.rmtree(b["unselected_dir"], ignore_errors=True)
            _remove_profiles_from_local_state(
                b["user_data_dir"],
                [SELECTED_TEST_PROFILE, UNSELECTED_TEST_PROFILE],
            )
        shutil.rmtree(tmp_root, ignore_errors=True)


@pytest.mark.app_check
@pytest.mark.app_clean
def test_010_PC정리_트리체크박스_일괄선택해제(clean_page: CleanPage):
    """
    [APP-06-02-010] PC정리 신규 안내 문구 및 트리 체크박스(전체·Windows 2개·웹 브라우저 5개) 일괄 선택/해제 검증
    """
    title = "체크박스 계층 선택·해제 및 신규 UI 항목"
    _print_section_header(title)
    try:
        # 1. 신규 안내 문구 확인 (브라우저 자동 종료 안내)
        notices = clean_page.get_clean_notice_items()
        print(f">>> [안내 문구] {notices}")
        assert any("선택한 브라우저가 실행 중이면 사용자 확인 후 자동으로 종료합니다" in n for n in notices), (
            f"신규 브라우저 자동 종료 안내 문구가 보이지 않습니다: {notices}"
        )

        # 2. 삭제된 구 항목 미노출 확인
        visible_cbs = clean_page.get_visible_checkbox_names()
        for old_item in DEPRECATED_BROWSER_ITEMS:
            assert old_item not in visible_cbs, f"개편으로 제거된 구 항목 '{old_item}'이 여전히 노출됩니다."

        clean_page.uncheck_all()
        for item in CleanPage.ALL_LEAF_ITEMS:
            assert clean_page.get_checkbox_state(item) == 0, f"초기화 후 '{item}'이 해제되지 않았습니다."

        # 3. 'Windows' 상위 체크박스 선택 -> 하위 2개 선택 확인
        clean_page.set_checkbox("Windows", True)
        for item in CleanPage.WINDOWS_ITEMS:
            assert clean_page.get_checkbox_state(item) == 1, f"'Windows' 선택 후 '{item}'이 선택되지 않았습니다."
        for item in CleanPage.BROWSER_ITEMS:
            assert clean_page.get_checkbox_state(item) == 0, f"'Windows' 선택 시 '{item}'은 해제 상태여야 합니다."

        # 4. '웹 브라우저' 상위 체크박스 선택 -> 신규 하위 5개 선택 및 '전체' 선택 확인
        clean_page.set_checkbox("웹 브라우저", True)
        for item in CleanPage.BROWSER_ITEMS:
            assert clean_page.get_checkbox_state(item) == 1, f"'웹 브라우저' 선택 후 '{item}'이 선택되지 않았습니다."
        assert clean_page.get_checkbox_state("전체") == 1, "모든 하위 항목 선택 시 '전체'도 선택 상태여야 합니다."

        # 5. '전체' 해제 -> 전체 항목 해제 확인
        clean_page.set_checkbox("전체", False)
        for item in CleanPage.ALL_LEAF_ITEMS:
            assert clean_page.get_checkbox_state(item) == 0, f"'전체' 해제 후 '{item}'이 해제되지 않았습니다."
        print(">>> [결과] 신규 안내 문구 및 전체 / Windows(2) / 웹 브라우저(5) 계층 선택·해제 정상")
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
        result = clean_page.run_clean_for_items(["윈도우 임시 파일"], timeout=20.0)
        exists_after = dummy_file.exists()
        print(f">>> [정리 후] 결과: {'삭제됨' if not exists_after else '미삭제'} | 모달={result['profile_results']}")
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

        result = clean_page.run_clean_for_items(["휴지통 비우기"], timeout=20.0)
        after_count = _get_recycle_bin_count()
        print(f">>> [정리 후] 휴지통 항목 수: {after_count} | 모달={result['profile_results']}")
        assert after_count == 0, f"휴지통 비우기 후에도 휴지통에 {after_count}개 항목이 남아 있습니다."
    finally:
        if dummy_file.exists():
            dummy_file.unlink(missing_ok=True)
        _print_section_footer(title)


@pytest.mark.app_check
@pytest.mark.app_clean
def test_040_웹브라우저_프로필선택UI_기본미선택_검증(clean_page: CleanPage, browser_test_env):
    """
    [APP-06-02-040] 확인 모달 브라우저별 프로필 탐지·표시(이름+폴더명), 기본 미선택 및 정리하기 버튼 활성화 제어 검증
    """
    if not browser_test_env:
        pytest.skip("설치된 Chrome/Edge 브라우저를 찾을 수 없습니다.")

    title = "웹 브라우저 프로필 선택 UI"
    _print_section_header(title)
    try:
        clean_page.uncheck_all()
        clean_page.set_checkbox("방문 기록", True)
        clean_page.click_clean_button()
        clean_page.wait_for_confirm_modal(timeout=5.0)

        try:
            info = clean_page.get_confirm_modal_info()
            print(f">>> [확인 모달 초기] profiles={info['profiles']}, confirm_enabled={info['confirm_enabled']}")

            # 1. 안내 문구 및 기본 미선택 시 '정리하기' 버튼 비활성화 검증
            assert any("프로필을 하나 이상 선택하세요" in t for t in info["texts"]), (
                f"프로필 미선택 안내 문구가 없습니다: {info['texts']}"
            )
            assert any("전체 기간" in t for t in info["texts"]), (
                f"전체 기간 고정 안내 문구가 없습니다: {info['texts']}"
            )
            assert info["confirm_enabled"] is False, (
                "프로필을 선택하지 않았는데 확인 모달의 '정리하기' 버튼이 활성화되어 있습니다."
            )

            # 2. 설치된 브라우저별 프로필 표시 및 기본 미선택 검증
            for b in browser_test_env:
                bname = b["name"]
                b_profs = info["profiles"].get(bname, [])
                folders = [p["folder"] for p in b_profs]
                assert b_profs, f"{bname}의 프로필 목록이 확인 모달에 표시되지 않았습니다: {info['profiles']}"
                if b.get("has_test_profiles"):
                    assert SELECTED_TEST_PROFILE in folders, f"{bname}에서 '{SELECTED_TEST_PROFILE}' 프로필이 탐지되지 않았습니다: {b_profs}"
                    assert UNSELECTED_TEST_PROFILE in folders, f"{bname}에서 '{UNSELECTED_TEST_PROFILE}' 프로필이 탐지되지 않았습니다: {b_profs}"
                assert all(p["checked"] == 0 for p in b_profs), f"{bname} 프로필 기본 상태가 모두 미선택(0)이 아닙니다: {b_profs}"
                assert info["browser_all_states"].get(bname) == 0, f"{bname} 전체 선택 체크박스가 기본 해제 상태가 아닙니다."

            # 3. 선택 프로필 1개 체크 시 '정리하기' 버튼 활성화 및 브라우저 전체 선택 일부선택(2) 전환 확인
            selectable = next((b for b in browser_test_env if b.get("has_test_profiles")), browser_test_env[0])
            first_browser = selectable["name"]
            target_folder = SELECTED_TEST_PROFILE if selectable.get("has_test_profiles") else info["profiles"][first_browser][0]["folder"]
            clean_page.select_profiles_in_confirm_modal({first_browser: [target_folder]})
            after_info = clean_page.get_confirm_modal_info()
            print(f">>> [프로필 선택 후] confirm_enabled={after_info['confirm_enabled']}, all_states={after_info['browser_all_states']}")
            assert after_info["confirm_enabled"] is True, "프로필을 선택했는데도 '정리하기' 버튼이 활성화되지 않았습니다."
            assert after_info["browser_all_states"].get(first_browser) in (1, 2), (
                f"{first_browser} 프로필 선택 후 상위 전체선택 체크박스 상태가 반영되지 않았습니다: {after_info['browser_all_states']}"
            )
        finally:
            clean_page.cancel_confirm_modal(timeout=5.0)
    finally:
        _print_section_footer(title)


@pytest.mark.app_check
@pytest.mark.app_clean
@pytest.mark.parametrize("category", CleanPage.BROWSER_ITEMS)
def test_050_웹브라우저_항목별_DB저장소_정리검증(clean_page: CleanPage, browser_test_env, category: str):
    """
    [APP-06-02-050] 신규 웹 브라우저 5개 항목별 선택 정리(DB·저장소 정밀 삭제), 보존 데이터 유지 및 미선택 프로필 무영향 검증
    """
    if not browser_test_env:
        pytest.skip("설치된 Chrome/Edge 브라우저를 찾을 수 없습니다.")

    title = f"웹 브라우저 - {category}"
    _print_section_header(title)
    try:
        # QA 대시보드를 띄우고 있는 브라우저는 taKeeper.exe가 전체 종료하므로,
        # 다른 브라우저가 함께 설치된 경우 대시보드 브라우저는 정리 대상에서 자동 제외해 대시보드 창을 보호합니다.
        non_dashboard = [b for b in browser_test_env if not b.get("is_dashboard_browser")]
        skipped_dashboard = [b["name"] for b in browser_test_env if b.get("is_dashboard_browser")]
        if non_dashboard and skipped_dashboard:
            clean_targets = non_dashboard
            print(
                f">>> [대시보드 보호] {skipped_dashboard}에서 QA 대시보드가 열려 있어 "
                f"창 종료 방지를 위해 {[b['name'] for b in clean_targets]} 대상으로 정리 검증합니다."
            )
        else:
            clean_targets = browser_test_env

        # 각 항목 테스트 전 선택 프로필(Profile 99) & 미선택 프로필(Profile 98) 재시드
        target_map: Dict[str, List[str]] = {}
        before_selected: Dict[str, Dict[str, Any]] = {}
        before_unselected: Dict[str, Dict[str, Any]] = {}

        for b in clean_targets:
            _seed_profile_data(b["selected_dir"], b["template_dir"], b["default_dir"])
            _seed_profile_data(b["unselected_dir"], b["template_dir"], b["default_dir"])
            target_map[b["name"]] = [SELECTED_TEST_PROFILE]
            before_selected[b["name"]] = _snapshot_profile(b["selected_dir"])
            before_unselected[b["name"]] = _snapshot_profile(b["unselected_dir"])

        print(f">>> [정리 대상] 항목='{category}', 선택 프로필={target_map} (미선택 대조군={UNSELECTED_TEST_PROFILE})")
        result = clean_page.run_clean_for_items([category], browser_profiles=target_map, timeout=30.0)
        print(f">>> [결과 모달] 요약='{result['summary_text']}', 프로필별={result['profile_results']}")

        errors: List[str] = []
        for b in clean_targets:
            bname = b["name"]
            after_sel = _snapshot_profile(b["selected_dir"])
            after_unsel = _snapshot_profile(b["unselected_dir"])
            print(f"    - [{bname}/{SELECTED_TEST_PROFILE}] 정리 전={before_selected[bname]}")
            print(f"    - [{bname}/{SELECTED_TEST_PROFILE}] 정리 후={after_sel}")

            # 1. 결과 모달에 해당 프로필별 상태가 '완료'로 표시되었는지 확인
            prof_key = f"{bname} {SELECTED_TEST_PROFILE}"
            status = result["profile_results"].get(prof_key)
            if status != "완료":
                errors.append(f"[{prof_key}] 결과 모달 상태가 '완료'가 아닙니다: 실제={status!r} (전체={result['texts']})")

            # 2. 보존 대상(Bookmarks) 및 미선택 프로필(Profile 98) 무결성 검증
            if not after_sel["bookmarks_exists"]:
                errors.append(f"[{prof_key}] 보존 대상인 Bookmarks 파일이 삭제되었습니다.")
            if after_unsel != before_unselected[bname]:
                errors.append(
                    f"[{bname} {UNSELECTED_TEST_PROFILE}] 미선택 프로필 데이터가 변경되었습니다: "
                    f"전={before_unselected[bname]} -> 후={after_unsel}"
                )

            # 3. 항목별 정밀 DB/저장소 정리 및 타 항목 데이터 독립 보존 검증
            if category == "방문 기록":
                if after_sel.get("history_urls") != 0 or after_sel.get("history_visits") != 0:
                    errors.append(f"[{prof_key}] 방문 기록(History.urls/visits)이 정리되지 않았습니다: {after_sel}")
                if before_selected[bname].get("history_downloads") == 1 and after_sel.get("history_downloads") != 1:
                    errors.append(f"[{prof_key}] '방문 기록'만 정리했는데 다운로드 기록까지 삭제되었습니다: {after_sel}")
            elif category == "다운로드 기록":
                if after_sel.get("history_downloads") != 0 or after_sel.get("history_downloads_url_chains") != 0:
                    errors.append(f"[{prof_key}] 다운로드 기록(History.downloads)이 정리되지 않았습니다: {after_sel}")
                if before_selected[bname].get("history_urls") == 1 and after_sel.get("history_urls") != 1:
                    errors.append(f"[{prof_key}] '다운로드 기록'만 정리했는데 방문 기록(urls)까지 삭제되었습니다: {after_sel}")
            elif category == "쿠키 및 기타 사이트 데이터":
                if after_sel.get("cookies_count") != 0:
                    errors.append(f"[{prof_key}] 쿠키(Network\\Cookies)가 정리되지 않았습니다: {after_sel}")
            elif category == "캐시된 이미지 및 파일":
                if after_sel.get("cache_data_exists") or after_sel.get("code_cache_exists"):
                    errors.append(f"[{prof_key}] 캐시 파일(Cache_Data / Code Cache)이 삭제되지 않았습니다: {after_sel}")
            elif category == "자동 완성 양식 데이터":
                if after_sel.get("autofill_count") != 0:
                    errors.append(f"[{prof_key}] 자동 완성 양식 데이터(Web Data.autofill)가 정리되지 않았습니다: {after_sel}")

        assert not errors, "\n".join(errors)
    finally:
        _print_section_footer(title)


@pytest.mark.app_check
@pytest.mark.app_clean
def test_060_실행중_브라우저_자동종료_및_정리검증(clean_page: CleanPage, browser_test_env):
    """
    [APP-06-02-060] 실행 중인 브라우저 감지 시 종료 안내 표시, '정리하기' 클릭 후 자동 종료 및 데이터 정리 완료 검증
    """
    if not browser_test_env:
        pytest.skip("설치된 Chrome/Edge 브라우저를 찾을 수 없습니다.")

    # 대시보드를 띄우지 않은 브라우저를 최우선 선택 (Edge 우선, 대시보드가 Edge면 Chrome 선택)
    non_dashboard = [b for b in browser_test_env if not b.get("is_dashboard_browser")]
    pool = non_dashboard or browser_test_env
    target_browser = next((b for b in pool if b["name"] == "Edge"), pool[0])
    bname = target_browser["name"]
    exe_name = target_browser["exe_name"]
    title = f"실행 중 브라우저({bname}) 자동 종료 및 정리"
    _print_section_header(title)

    try:
        if not target_browser.get("is_dashboard_browser"):
            _kill_process(exe_name)
        _seed_profile_data(target_browser["selected_dir"], target_browser["template_dir"], target_browser["default_dir"])

        # 대상 브라우저 실제 실행 (미선택 프로필로 창 띄워 실행 중 상태 구성)
        subprocess.Popen(
            [
                str(target_browser["exe_path"]),
                f"--profile-directory={UNSELECTED_TEST_PROFILE}",
                "--no-first-run",
                "--no-default-browser-check",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        start_dl = time.time() + 6.0
        while time.time() < start_dl and not _is_process_running(exe_name):
            time.sleep(0.2)
        assert _is_process_running(exe_name), f"테스트 대상 브라우저({exe_name}) 실행에 실패했습니다."
        time.sleep(1.0)

        clean_page.bring_to_front()
        clean_page.uncheck_all()
        clean_page.set_checkbox("캐시된 이미지 및 파일", True)
        clean_page.click_clean_button()
        clean_page.wait_for_confirm_modal(timeout=5.0)
        clean_page.select_profiles_in_confirm_modal({bname: [SELECTED_TEST_PROFILE]})

        # 1. 확인 모달에 실행 중 브라우저 종료 안내 문구 노출 확인
        confirm_info = clean_page.get_confirm_modal_info()
        print(f">>> [종료 안내 확인] warnings={confirm_info['running_browser_warnings']}")
        assert confirm_info["has_running_browser_warning"], (
            f"{bname} 실행 중인데 확인 모달에 브라우저 자동 종료 경고 문구가 표시되지 않았습니다: {confirm_info['texts']}"
        )
        assert any(bname in w for w in confirm_info["running_browser_warnings"]), (
            f"종료 경고 문구에 대상 브라우저명('{bname}')이 포함되지 않았습니다: {confirm_info['running_browser_warnings']}"
        )

        # 2. 정리하기 실행 -> 진행 상태 거쳐 완료 대기
        clean_page.confirm_clean(timeout=5.0)
        result = clean_page.wait_for_complete_modal(timeout=35.0)
        print(f">>> [진행 상태 관찰] {result.get('progress_texts')}")
        print(f">>> [결과 모달] {result['profile_results']}")
        clean_page.close_complete_modal(timeout=5.0)

        # 3. 대상 브라우저 프로세스 자동 종료 및 캐시 정리 완료 검증
        time.sleep(0.5)
        still_running = _is_process_running(exe_name)
        after_sel = _snapshot_profile(target_browser["selected_dir"])
        print(f">>> [정리 후] {exe_name} 실행중={still_running}, 캐시상태={after_sel}")

        assert not still_running, f"정리하기 완료 후에도 {exe_name} 프로세스가 종료되지 않았습니다."
        assert result["profile_results"].get(f"{bname} {SELECTED_TEST_PROFILE}") == "완료", (
            f"실행 중 브라우저 자동 종료 후 정리 상태가 '완료'가 아닙니다: {result['profile_results']}"
        )
        assert not after_sel["cache_data_exists"] and not after_sel["code_cache_exists"], (
            f"실행 중 브라우저 종료 후 캐시 파일이 삭제되지 않았습니다: {after_sel}"
        )
    finally:
        if not target_browser.get("is_dashboard_browser"):
            _kill_process(exe_name)
        _print_section_footer(title)
