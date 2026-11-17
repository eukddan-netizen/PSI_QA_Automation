"""
OS 버전, 백신 및 방화벽 상태 연동 테스트 (Row 48~50)
1. OS VERSION: winver의 OS 버전 및 에디션과 PC정리 탭 UI 일치 검증
2. ANTIVIRUS: PC에 설치된 백신 목록/상태 확인 및 실시간 보호 ON/OFF -> 새로고침 동기화 검증
3. FIREWALL: PC에 설치된 방화벽 목록/상태 확인 및 방화벽 ON/OFF -> 새로고침 동기화 검증
"""

import json
import re
import subprocess
import time
from typing import Dict, List, Optional, Tuple

import pytest
import win32gui
from pywinauto import Application

from common.os_utils import require_admin, run_cmd
from core.app_controller import AppController
from pages.client.clean_page import CleanPage


def _get_winver_info() -> Dict[str, str]:
    """
    winver.exe를 실행하여 실제 Windows 정보 다이얼로그의 OS 에디션 및 버전(예: 25H2)을 추출합니다.
    (메인 프로세스의 switch_to_user_desktop 영향을 받지 않도록 독립 서브프로세스에서 조회)
    """
    import sys

    script = (
        "import json, re, subprocess, time, win32gui\n"
        "from pywinauto import Application\n"
        "p = subprocess.Popen(['winver.exe'])\n"
        "try:\n"
        "    hwnd = 0\n"
        "    deadline = time.time() + 6.0\n"
        "    while time.time() < deadline:\n"
        "        hwnd = win32gui.FindWindow(None, 'Windows 정보') or win32gui.FindWindow(None, 'About Windows')\n"
        "        if hwnd and win32gui.IsWindowVisible(hwnd):\n"
        "            break\n"
        "        time.sleep(0.2)\n"
        "    if not hwnd:\n"
        "        raise TimeoutError('winver.exe 창을 찾지 못했습니다.')\n"
        "    app = Application(backend='uia').connect(handle=hwnd)\n"
        "    win = app.window(handle=hwnd)\n"
        "    texts = [(d.element_info.name or '').strip() for d in win.descendants(control_type='Text') if d.element_info.name]\n"
        "    display_version, edition = '', ''\n"
        "    for txt in texts:\n"
        "        m_ver = re.search(r'(?:버전|Version)\\s+([0-9A-Za-z]+)\\s*\\(', txt)\n"
        "        if m_ver and not display_version:\n"
        "            display_version = m_ver.group(1).strip()\n"
        "        m_ed = re.match(r'^(Windows\\s+.+?)\\s+(?:운영\\s*체제|operating\\s+system)', txt, re.IGNORECASE)\n"
        "        if m_ed and not edition:\n"
        "            edition = m_ed.group(1).strip()\n"
        "    print(json.dumps({'edition': edition, 'display_version': display_version, 'raw_texts': ' | '.join(texts)}))\n"
        "finally:\n"
        "    try:\n"
        "        p.terminate()\n"
        "        p.wait(timeout=3)\n"
        "    except Exception:\n"
        "        pass\n"
    )
    res = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )
    if res.returncode != 0 or not res.stdout.strip():
        raise RuntimeError(f"winver 정보 조회 실패: {res.stderr.strip() or res.stdout.strip()}")
    return json.loads(res.stdout.strip().splitlines()[-1])


def _query_security_center(class_name: str) -> List[Dict[str, str]]:
    """
    root/SecurityCenter2에서 AntivirusProduct 또는 FirewallProduct 목록을 조회합니다.
    productState의 0x1000 비트로 ON/OFF를 판별합니다.
    """
    ps_cmd = (
        f"Get-CimInstance -Namespace root/SecurityCenter2 -ClassName {class_name} "
        "| Select-Object displayName, productState | ConvertTo-Json -Compress"
    )
    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if res.returncode != 0 or not res.stdout.strip():
        return []

    data = json.loads(res.stdout.strip())
    if isinstance(data, dict):
        data = [data]

    products: List[Dict[str, str]] = []
    for item in data:
        name = (item.get("displayName") or "").strip()
        state = int(item.get("productState") or 0)
        if not name:
            continue
        products.append({
            "name": name,
            "state": "ON" if (state & 0x1000) else "OFF",
        })
    return products


def _get_defender_realtime_status() -> Dict[str, Optional[bool]]:
    """Windows Defender의 실시간 보호 및 변조 보호 상태를 조회합니다."""
    ps_cmd = (
        "Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled, IsTamperProtected "
        "| ConvertTo-Json -Compress"
    )
    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if res.returncode != 0 or not res.stdout.strip():
        return {"enabled": None, "realtime": None, "tamper": None}

    data = json.loads(res.stdout.strip())
    return {
        "enabled": data.get("AntivirusEnabled"),
        "realtime": data.get("RealTimeProtectionEnabled"),
        "tamper": data.get("IsTamperProtected"),
    }


def _set_defender_realtime(enable: bool) -> None:
    """Windows Defender 실시간 보호 ON/OFF 설정"""
    disable_flag = "$false" if enable else "$true"
    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"Set-MpPreference -DisableRealtimeMonitoring {disable_flag}"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Set-MpPreference 실패: {res.stderr.strip() or res.stdout.strip()}")


def _get_windows_firewall_profile_states() -> Dict[str, str]:
    """netsh advfirewall로 Domain/Private/Public 프로필별 ON/OFF 상태 조회"""
    profile_map = {
        "domainprofile": "Domain",
        "privateprofile": "Private",
        "publicprofile": "Public",
    }
    states: Dict[str, str] = {}
    for netsh_key, label in profile_map.items():
        rc, out, _ = run_cmd(["netsh", "advfirewall", "show", netsh_key, "state"])
        if rc != 0:
            continue
        state = "OFF"
        for line in out.splitlines():
            if line.strip().lower().startswith("state") or "상태" in line:
                if "ON" in line.upper() or "사용" in line:
                    state = "ON"
                    break
        states[netsh_key] = state
    return states


def _wait_for_item_state(
    fetch_fn,
    refresh_fn,
    target_name: str,
    expected_state: str,
    timeout: float = 10.0,
) -> Optional[str]:
    """새로고침 버튼을 누르며 특정 항목의 UI 상태가 expected_state('ON'/'OFF')가 될 때까지 대기"""
    deadline = time.time() + timeout
    last_state: Optional[str] = None
    while time.time() < deadline:
        refresh_fn()
        items = fetch_fn()
        for item in items:
            if item["name"].lower() == target_name.lower():
                last_state = item["state"]
                if last_state == expected_state:
                    return last_state
        time.sleep(0.8)
    return last_state


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
def test_os_version_display(clean_page: CleanPage):
    """PC정리 탭의 OS VERSION 정보와 실제 winver 정보 일치 검증"""
    winver = _get_winver_info()
    print(f"\n>>> [winver] edition='{winver['edition']}', version='{winver['display_version']}'")
    assert winver["edition"], f"winver에서 OS 에디션을 파싱하지 못했습니다: {winver['raw_texts']}"

    ui_os_text = clean_page.get_os_version_text()
    print(f">>> [UI OS VERSION] '{ui_os_text}'")

    assert winver["edition"] in ui_os_text, (
        f"UI OS VERSION('{ui_os_text}')에 winver 에디션('{winver['edition']}')이 포함되지 않았습니다."
    )
    if winver["display_version"]:
        assert winver["display_version"] in ui_os_text, (
            f"UI OS VERSION('{ui_os_text}')에 winver 버전('{winver['display_version']}')이 포함되지 않았습니다."
        )


@pytest.mark.app_check
@pytest.mark.app_clean
def test_antivirus_detection_match(clean_page: CleanPage):
    """PC에 설치된 ANTIVIRUS 제품 목록 및 ON/OFF 상태와 PC정리 탭 UI 일치 검증"""
    pc_avs = _query_security_center("AntivirusProduct")
    print(f"\n>>> [PC SecurityCenter2 AntivirusProduct] {pc_avs}")
    assert pc_avs, "SecurityCenter2에서 조회된 백신 제품이 없습니다."

    ui_avs = clean_page.get_antivirus_items()
    print(f">>> [UI ANTIVIRUS] {ui_avs}")

    pc_map = {item["name"]: item["state"] for item in pc_avs}
    ui_map = {item["name"]: item["state"] for item in ui_avs}

    assert ui_map == pc_map, f"UI ANTIVIRUS 목록/상태({ui_map})가 PC 실제 백신 상태({pc_map})와 다릅니다."


@pytest.mark.app_check
@pytest.mark.app_clean
def test_antivirus_status_sync(clean_page: CleanPage):
    """실시간 보호 ON/OFF 전환 후 새로고침 아이콘 클릭 시 ANTIVIRUS 상태 동기화 검증"""
    require_admin("백신 실시간 보호 기능 ON/OFF 제어에는 Windows 관리자 권한이 필요합니다.")

    pc_avs = _query_security_center("AntivirusProduct")
    other_active_avs = [a["name"] for a in pc_avs if a["name"] != "Windows Defender" and a["state"] == "ON"]
    mp_status = _get_defender_realtime_status()
    print(f"\n>>> [AV 상태] SecurityCenter2={pc_avs}, MpStatus={mp_status}")

    if other_active_avs and not mp_status.get("enabled"):
        pytest.skip(
            f"타사 백신({', '.join(other_active_avs)})이 활성 상태여서 Windows Defender가 비활성(스누즈) 상태입니다. "
            "CLI로 타사 백신 실시간 보호를 자동 전환할 수 없어 동기화 테스트를 건너뜁니다."
        )
    if mp_status.get("tamper"):
        pytest.skip("Windows Defender 변조 보호(Tamper Protection)가 켜져 있어 실시간 보호 자동 전환이 차단됩니다.")
    if mp_status.get("realtime") is None:
        pytest.skip("Windows Defender 실시간 보호 상태를 조회할 수 없습니다.")

    orig_realtime = bool(mp_status["realtime"])
    target_realtime = not orig_realtime
    expected_toggled_str = "ON" if target_realtime else "OFF"
    expected_restored_str = "ON" if orig_realtime else "OFF"

    try:
        _set_defender_realtime(target_realtime)
        actual_state = _wait_for_item_state(
            clean_page.get_antivirus_items,
            clean_page.click_antivirus_refresh,
            "Windows Defender",
            expected_toggled_str,
            timeout=12.0,
        )
        assert actual_state == expected_toggled_str, (
            f"실시간 보호 {expected_toggled_str} 전환 후 새로고침 시 UI 상태가 '{expected_toggled_str}'이 아닙니다: '{actual_state}'"
        )
    finally:
        try:
            _set_defender_realtime(orig_realtime)
        except Exception as exc:
            print(f">>> [원복 경고] Windows Defender 실시간 보호 원복 실패: {exc}")

    restored_state = _wait_for_item_state(
        clean_page.get_antivirus_items,
        clean_page.click_antivirus_refresh,
        "Windows Defender",
        expected_restored_str,
        timeout=12.0,
    )
    assert restored_state == expected_restored_str, (
        f"실시간 보호 원복({expected_restored_str}) 후 새로고침 시 UI 상태가 복구되지 않았습니다: '{restored_state}'"
    )


@pytest.mark.app_check
@pytest.mark.app_clean
def test_firewall_detection_match(clean_page: CleanPage):
    """PC에 설치된 FIREWALL 목록 및 ON/OFF 상태와 PC정리 탭 UI 일치 검증"""
    profile_states = _get_windows_firewall_profile_states()
    win_fw_state = "ON" if any(v == "ON" for v in profile_states.values()) else "OFF"

    expected_map: Dict[str, str] = {"Windows Defender Firewall": win_fw_state}
    for fw in _query_security_center("FirewallProduct"):
        expected_map[fw["name"]] = fw["state"]

    print(f"\n>>> [PC 방화벽] profiles={profile_states}, expected={expected_map}")

    ui_fws = clean_page.get_firewall_items()
    ui_map = {item["name"]: item["state"] for item in ui_fws}
    print(f">>> [UI FIREWALL] {ui_map}")

    assert ui_map == expected_map, f"UI FIREWALL 목록/상태({ui_map})가 PC 실제 방화벽 상태({expected_map})와 다릅니다."


@pytest.mark.app_check
@pytest.mark.app_clean
def test_firewall_status_sync(clean_page: CleanPage):
    """활성 상태인 방화벽 ON/OFF 전환 후 새로고침 아이콘 클릭 시 FIREWALL 상태 동기화 검증"""
    require_admin("Windows 방화벽 ON/OFF 제어에는 Windows 관리자 권한이 필요합니다.")

    orig_profiles = _get_windows_firewall_profile_states()
    assert orig_profiles, "Windows 방화벽 프로필 상태를 조회하지 못했습니다."

    orig_any_on = any(v == "ON" for v in orig_profiles.values())
    toggled_cmd = "off" if orig_any_on else "on"
    expected_toggled_str = "OFF" if orig_any_on else "ON"
    expected_restored_str = "ON" if orig_any_on else "OFF"

    try:
        run_cmd(["netsh", "advfirewall", "set", "allprofiles", "state", toggled_cmd], check=True)
        actual_state = _wait_for_item_state(
            clean_page.get_firewall_items,
            clean_page.click_firewall_refresh,
            "Windows Defender Firewall",
            expected_toggled_str,
            timeout=10.0,
        )
        assert actual_state == expected_toggled_str, (
            f"방화벽 {expected_toggled_str} 전환 후 새로고침 시 UI 상태가 '{expected_toggled_str}'이 아닙니다: '{actual_state}'"
        )
    finally:
        for prof_key, orig_state in orig_profiles.items():
            try:
                run_cmd(["netsh", "advfirewall", "set", prof_key, "state", orig_state.lower()], check=True)
            except Exception as exc:
                print(f">>> [원복 경고] 방화벽({prof_key}) 원복 실패: {exc}")

    restored_state = _wait_for_item_state(
        clean_page.get_firewall_items,
        clean_page.click_firewall_refresh,
        "Windows Defender Firewall",
        expected_restored_str,
        timeout=10.0,
    )
    assert restored_state == expected_restored_str, (
        f"방화벽 원복({expected_restored_str}) 후 새로고침 시 UI 상태가 복구되지 않았습니다: '{restored_state}'"
    )
