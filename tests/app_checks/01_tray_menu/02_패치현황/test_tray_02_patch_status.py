"""
[대분류: 트레이 아이콘 > 중분류 2: 패치 현황]

- 2_0001: 트레이 아이콘 우클릭 > 패치 현황 -> 권고패치 현황/설치 패치 목록과
          웹 관리자(/patch -> 사용자 검색 -> 권고 개수 클릭 -> 패치 정보 모달 발표일) 정합성 검증
"""

from collections import Counter
import time
import pytest

from common.os_utils import get_current_machine_ips, require_admin
from pages.tray_patch_status_page import TrayPatchStatusPage


def _log_tray_patch_data(summary: dict, installed_list: list) -> None:
    """트레이 '패치 현황'에서 수집한 권고패치 현황 및 설치 패치 목록을 터미널에 출력"""
    print("\n================ [트레이 아이콘 수집: 권고패치 현황] ================", flush=True)
    for cat, stats in summary.items():
        print(
            f"  - {cat:<12} | 전체: {stats['total']:>2}개 | 설치: {stats['installed']:>2}개 | 패치율: {stats['rate_text']}",
            flush=True,
        )
    print(f"================ [트레이 아이콘 수집: 설치 패치 목록 ({len(installed_list)}건)] ================", flush=True)
    for idx, item in enumerate(installed_list, start=1):
        print(f"  [{idx:>2}] {item['type']:<10} | {item['name']} | 발표일: {item['release_date']}", flush=True)


def _log_web_patch_data(matched_ip: str, web_installed_count: int, web_total_count: int, web_patches: list) -> None:
    """웹 관리자(/patch, /patch/client)에서 수집한 권고 패치 정보를 터미널에 출력"""
    cat_total = Counter(p["type"] for p in web_patches)
    cat_installed = Counter(p["type"] for p in web_patches if p["installed"])
    print(
        f"\n================ [서버 수집({matched_ip}): 유형별 권고 패치 집계 ({web_installed_count}/{web_total_count}개)] ================",
        flush=True,
    )
    for cat in sorted(cat_total.keys()):
        print(f"  - {cat:<12} | 전체: {cat_total[cat]:>2}개 | 설치: {cat_installed.get(cat, 0):>2}개", flush=True)
    print(f"================ [서버 수집: 권고 패치 상세 목록 ({len(web_patches)}건)] ================", flush=True)
    for idx, p in enumerate(web_patches, start=1):
        status_one_line = p["status"].replace("\n", " ")
        rel = p["release_date"] or "-"
        print(
            f"  [{idx:>2}] {p['type']:<10} | {p['name']} | 상태: {status_one_line} | 발표일: {rel}",
            flush=True,
        )


def _assert_rate_consistent(label: str, total: int, installed: int, rate_value: int) -> None:
    """패치율(%) 수치 일관성 검증"""
    if total == 0:
        assert rate_value == 0, f"[{label}] 전체 0개일 때 패치율은 0%여야 합니다. (실제: {rate_value}%)"
    elif installed == total:
        assert rate_value == 100, f"[{label}] 전체 설치 시 패치율은 100%여야 합니다. (실제: {rate_value}%)"
    else:
        expected = installed * 100 / total
        assert abs(rate_value - expected) <= 1.0, (
            f"[{label}] 패치율 불일치! 기대: ~{expected:.1f}%, 실제: {rate_value}%"
        )


@pytest.mark.app_check
@pytest.mark.app_tray
@pytest.mark.tray_02
def test_patch_status_matches_admin_web(patch_admin_page, app_ctrl):
    """
    [TC: 2_0001]
    - 조건: 정상 동작
    - 액션:
      1. 트레이 아이콘 우클릭 > '패치 현황' 클릭 및 권고패치 현황/설치 패치 목록 수집
      2. https://192.168.4.151/patch에서 ipconfig 기반 현재 PC IP 검색 및 '권고' 개수 클릭
      3. 상세 테이블 및 각 패치 정보 모달의 '발표일' 수집 후 트레이 결과와 비교 검증
    - 기대 결과: 권고패치 현황(종류별 전체/설치/패치율, 총계) 및 설치 패치 목록(종류, 이름, 발표일) 100% 일치
    """
    require_admin(
        "보안 에이전트(taAssistant) 트레이 우클릭 메뉴 제어(Windows UIPI 제약 우회)를 위해 "
        "PowerShell을 '관리자 권한으로 실행(Run as Administrator)'해야 합니다."
    )

    # 1. 트레이 > 패치 현황 팝업 열기 및 데이터 수집
    app_ctrl.close_hr_ui()
    time.sleep(0.5)
    app_ctrl.click_tray_menu_item("패치 현황")

    tray_popup = TrayPatchStatusPage(timeout=10.0)
    assert tray_popup.is_visible(), "트레이 > '패치 현황' 클릭 후 팝업 창이 노출되어야 합니다."
    try:
        tray_summary, tray_installed_list = tray_popup.read_patch_status(timeout=10.0)
    finally:
        tray_popup.close()

    assert "총계" in tray_summary, f"권고패치 현황에 '총계' 행이 없습니다: {list(tray_summary.keys())}"
    tray_total_row = tray_summary["총계"]
    _log_tray_patch_data(tray_summary, tray_installed_list)

    # 트레이 내부 합계 정합성 검증
    categories = {k: v for k, v in tray_summary.items() if k != "총계"}
    assert sum(v["total"] for v in categories.values()) == tray_total_row["total"], (
        "트레이 권고패치 현황 종류별 '전체' 합계가 '총계'와 다릅니다."
    )
    assert sum(v["installed"] for v in categories.values()) == tray_total_row["installed"], (
        "트레이 권고패치 현황 종류별 '설치' 합계가 '총계'와 다릅니다."
    )
    assert len(tray_installed_list) == tray_total_row["installed"], (
        f"트레이 설치 패치 목록 행 수({len(tray_installed_list)})가 총계 설치 수({tray_total_row['installed']})와 다릅니다."
    )

    # 2. 관리자 웹(/patch)에서 현재 PC IP 검색
    ip_candidates = get_current_machine_ips()
    print(f">>> [2_0001] ipconfig/라우팅 기반 현재 PC IP 후보: {ip_candidates}")
    matched_ip, user_row = patch_admin_page.search_user_by_ip(ip_candidates)

    web_installed_count, web_total_count = patch_admin_page.get_user_recommended_counts(user_row)
    print(f">>> [2_0001] 관리자 웹({matched_ip}) 권고 카운트: {web_installed_count}/{web_total_count}개")

    assert tray_total_row["total"] == web_total_count, (
        f"권고 전체 개수 불일치! 트레이={tray_total_row['total']}, 웹={web_total_count}"
    )
    assert tray_total_row["installed"] == web_installed_count, (
        f"권고 설치 개수 불일치! 트레이={tray_total_row['installed']}, 웹={web_installed_count}"
    )

    # 3. '권고' 개수 클릭 -> 상세 목록 및 모달 '발표일' 수집
    patch_admin_page.click_user_recommended_count(user_row)
    web_patches = patch_admin_page.collect_recommended_patches()
    _log_web_patch_data(matched_ip, web_installed_count, web_total_count, web_patches)

    assert len(web_patches) == web_total_count, (
        f"상세 목록 행 수({len(web_patches)})가 사용자 권고 전체 개수({web_total_count})와 다릅니다."
    )

    web_installed_patches = [p for p in web_patches if p["installed"]]
    assert len(web_installed_patches) == web_installed_count, (
        f"상세 목록 설치 완료 행 수({len(web_installed_patches)})가 사용자 권고 설치 개수({web_installed_count})와 다릅니다."
    )

    # 4-1. 종류별 권고패치 현황(전체, 설치, 패치율) 비교 검증
    web_cat_total: Counter[str] = Counter(p["type"] for p in web_patches)
    web_cat_installed: Counter[str] = Counter(p["type"] for p in web_installed_patches)

    missing_cats = set(web_cat_total.keys()) - set(categories.keys())
    assert not missing_cats, f"웹 상세 패치 유형이 트레이 권고패치 현황에 누락되었습니다: {missing_cats}"

    for cat, stats in categories.items():
        exp_total = web_cat_total.get(cat, 0)
        exp_installed = web_cat_installed.get(cat, 0)
        assert stats["total"] == exp_total, (
            f"[{cat}] 전체 개수 불일치! 트레이={stats['total']}, 웹={exp_total}"
        )
        assert stats["installed"] == exp_installed, (
            f"[{cat}] 설치 개수 불일치! 트레이={stats['installed']}, 웹={exp_installed}"
        )
        _assert_rate_consistent(cat, stats["total"], stats["installed"], stats["rate_value"])

    _assert_rate_consistent("총계", tray_total_row["total"], tray_total_row["installed"], tray_total_row["rate_value"])

    # 4-2. 설치 패치 목록(종류, 이름, 발표일) 1:1 비교 검증
    tray_item_counts = Counter((p["type"], p["name"], p["release_date"]) for p in tray_installed_list)
    web_item_counts = Counter((p["type"], p["name"], p["release_date"]) for p in web_installed_patches)

    only_in_tray = list((tray_item_counts - web_item_counts).elements())
    only_in_web = list((web_item_counts - tray_item_counts).elements())
    assert tray_item_counts == web_item_counts, (
        "설치 패치 목록 불일치!\n"
        f"  트레이에만 있음: {only_in_tray}\n"
        f"  웹에만 있음: {only_in_web}"
    )

    print(f">>> [2_0001] 권고패치 현황 및 설치 패치 {len(web_installed_patches)}건(종류/이름/발표일) 100% 일치 검증 완료!")

