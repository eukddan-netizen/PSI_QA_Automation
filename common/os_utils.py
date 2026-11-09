"""
여러 점검이 공통으로 사용하는 OS 제어 및 원복(백업/복구) 유틸리티
- 레지스트리 읽기/쓰기 및 원본 백업·복구
- Windows 명령어(net user, net share, net accounts 등) 실행 및 계정 상태 백업·복구
- 점검별 handler.py 동적 로더 (53개 동일 파일명 충돌 방지)
- checks/catalog.yaml 로더
"""

import ctypes
import importlib.util
import shutil
import subprocess
import sys
import winreg
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = PROJECT_ROOT / "checks" / "catalog.yaml"

HIVE_MAP = {
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
}

HIVE_NAME_MAP = {
    winreg.HKEY_CURRENT_USER: "HKCU",
    winreg.HKEY_LOCAL_MACHINE: "HKLM",
}


def resolve_hive(hive: Any) -> int:
    if isinstance(hive, int):
        return hive
    return HIVE_MAP[str(hive).upper()]


def read_reg_value(hive: Any, subkey: str, value_name: str) -> Tuple[bool, Any, Optional[int]]:
    """
    레지스트리 값을 조회하여 (존재여부, 값, 타입) 반환.
    키나 값이 없으면 (False, None, None) 반환.
    """
    hkey = resolve_hive(hive)
    try:
        with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ) as key:
            val, reg_type = winreg.QueryValueEx(key, value_name)
            return True, val, reg_type
    except FileNotFoundError:
        return False, None, None


def write_reg_value(hive: Any, subkey: str, value_name: str, value: Any, reg_type: int = winreg.REG_DWORD) -> None:
    """레지스트리 값을 기록 (키가 없으면 생성)."""
    hkey = resolve_hive(hive)
    with winreg.CreateKeyEx(hkey, subkey, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, value_name, 0, reg_type, value)


def delete_reg_value(hive: Any, subkey: str, value_name: str) -> None:
    """레지스트리 값을 삭제 (이미 없으면 무시)."""
    hkey = resolve_hive(hive)
    try:
        with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, value_name)
    except FileNotFoundError:
        pass


def run_cmd(cmd: List[str] | str, check: bool = False) -> Tuple[int, str, str]:
    """
    Windows 명령어(net, powercfg, bcdedit 등) 실행 후 (returncode, stdout, stderr) 반환.
    한국어 Windows 콘솔(cp949) 인코딩을 안전하게 처리합니다.
    """
    res = subprocess.run(
        cmd,
        shell=isinstance(cmd, str),
        capture_output=True,
        text=True,
        encoding="cp949",
        errors="replace",
    )
    if check and res.returncode != 0:
        raise RuntimeError(f"명령 실행 실패 ({cmd}): {res.stderr.strip() or res.stdout.strip()}")
    return res.returncode, res.stdout, res.stderr


def is_local_user_active(username: str) -> Optional[bool]:
    """
    `net user <username>` 출력을 파싱하여 계정 활성화 여부(True/False) 반환.
    계정이 존재하지 않으면 None 반환.
    """
    rc, out, _ = run_cmd(["net", "user", username])
    if rc != 0:
        return None
    for line in out.splitlines():
        normalized = line.strip()
        if normalized.startswith("계정 활성") or normalized.lower().startswith("account active"):
            val = normalized.split()[-1].upper()
            return val in ("YES", "예", "Y")
    return None


def set_local_user_active(username: str, active: bool) -> None:
    """`net user <username> /active:yes|no` 명령으로 로컬 계정 활성 상태를 변경."""
    flag = "yes" if active else "no"
    rc, out, err = run_cmd(["net", "user", username, f"/active:{flag}"])
    if rc != 0:
        raise RuntimeError(f"'{username}' 계정 활성화({flag}) 변경 실패: {err.strip() or out.strip()}")


def is_admin() -> bool:
    """현재 프로세스가 Windows 관리자 권한(Elevated)으로 실행 중인지 확인합니다."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def require_admin() -> None:
    """관리자 권한이 필요한 점검을 비관리자 콘솔에서 실행할 때 안전하게 스킵합니다."""
    if not is_admin():
        pytest.skip("이 점검의 OS 상태 주입에는 Windows 관리자 권한(Run as Administrator)이 필요합니다.")


class StateGuard:
    """
    테스트 전 OS 설정을 백업하고, 테스트가 중간에 실패하거나 끝나더라도
    반드시 원래 상태로 복구(LIFO 순서)하는 안전장치.
    """

    def __init__(self) -> None:
        self._restorers: List[Tuple[str, Callable[[], None]]] = []
        self._backed_up_keys: set = set()

    def add_restore(self, description: str, restore_fn: Callable[[], None]) -> None:
        """사용자 정의 원복 콜백 등록."""
        self._restorers.append((description, restore_fn))

    def set_reg(self, hive: Any, subkey: str, value_name: str, value: Any, reg_type: int = winreg.REG_DWORD) -> None:
        """원래 레지스트리 값을 조회한 뒤 새 값을 기록하고, 성공 시 원복 콜백을 등록합니다."""
        hkey = resolve_hive(hive)
        hive_label = HIVE_NAME_MAP.get(hkey, str(hive))
        reg_id = (hkey, subkey.lower(), value_name.lower())
        need_backup = reg_id not in self._backed_up_keys
        existed, orig_val, orig_type = (False, None, None)
        if need_backup:
            existed, orig_val, orig_type = read_reg_value(hkey, subkey, value_name)

        write_reg_value(hkey, subkey, value_name, value, reg_type)

        if need_backup:
            self._backed_up_keys.add(reg_id)

            def _restore() -> None:
                if existed and orig_type is not None:
                    write_reg_value(hkey, subkey, value_name, orig_val, orig_type)
                else:
                    delete_reg_value(hkey, subkey, value_name)

            desc = f"레지스트리 원복 [{hive_label}\\{subkey} -> {value_name} = {orig_val if existed else '<삭제>'}]"
            self.add_restore(desc, _restore)

    def set_user_active(self, username: str, active: bool) -> None:
        """로컬 사용자 계정의 원래 활성 상태를 조회한 뒤 변경하고, 성공 시 원복 콜백을 등록합니다."""
        key_id = ("user_active", username.lower())
        need_backup = key_id not in self._backed_up_keys
        orig_active = is_local_user_active(username) if need_backup else None

        set_local_user_active(username, active)

        if need_backup and orig_active is not None:
            self._backed_up_keys.add(key_id)

            def _restore() -> None:
                set_local_user_active(username, orig_active)

            self.add_restore(f"로컬 계정 '{username}' 활성 상태 원복 (active={orig_active})", _restore)

    def restore_all(self) -> List[str]:
        """등록된 모든 원복 작업을 역순(LIFO)으로 실행하고 오류 목록을 반환합니다."""
        errors: List[str] = []
        while self._restorers:
            desc, fn = self._restorers.pop()
            try:
                print(f">>> [Teardown 원복] {desc}")
                fn()
            except Exception as exc:
                err_msg = f"[원복 실패] {desc}: {exc}"
                print(err_msg)
                errors.append(err_msg)
        self._backed_up_keys.clear()
        return errors


def load_check_handler(caller_file: str | Path):
    """
    점검 폴더 안의 `handler.py`를 폴더명 기반 고유 모듈 이름으로 동적 로드합니다.
    53개 폴더에 모두 `handler.py`가 있어도 sys.modules 충돌이 발생하지 않습니다.
    """
    check_dir = Path(caller_file).resolve().parent
    handler_path = check_dir / "handler.py"
    if not handler_path.exists():
        raise FileNotFoundError(f"핸들러 파일을 찾을 수 없습니다: {handler_path}")

    module_name = f"psi_checks_{check_dir.name}_handler"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, handler_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"핸들러 모듈 스펙 생성 실패: {handler_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_catalog() -> Dict[int, Dict[str, Any]]:
    """`checks/catalog.yaml`을 읽어 점검 번호(int)를 키로 하는 딕셔너리로 반환합니다."""
    if not CATALOG_PATH.exists():
        return {}
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    checks_list = data.get("checks", [])
    return {int(item["id"]): item for item in checks_list}


def get_check_meta(check_num: int) -> Dict[str, Any]:
    """특정 점검 번호의 카탈로그 메타데이터를 반환합니다."""
    catalog = load_catalog()
    if check_num not in catalog:
        raise KeyError(f"catalog.yaml에 {check_num}번 점검 정보가 없습니다.")
    return catalog[check_num]
