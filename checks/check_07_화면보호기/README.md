# 07. 화면 보호기 설정 여부 점검 (`check_07_화면보호기`)

- **자동화 난이도**: Tier A (레지스트리 제어 및 단일 클릭 즉시 조치 가능)
- **구현 상태**: 구현 완료 (`implemented`)
- **마커**: `check07`, `tier_a`

## 1. 점검 대상 및 판정 기준
- **점검 대상**: Windows 화면 보호기 대기 시간 및 다시 시작할 때 로그온 화면 표시 설정 여부 (`HKCU\Control Panel\Desktop`)
- **양호(안전) 기준**:
  - `ScreenSaveActive = "1"` (화면 보호기 활성화)
  - `ScreenSaveTimeOut <= "600"` (대기 시간 10분 이하)
  - `ScreenSaverIsSecure = "1"` (다시 시작할 때 로그온 화면 표시 체크)
  - **안내 문구**: `화면 보호기가 안전하게 설정되어 있습니다.`
- **취약 기준**:
  - 대기 시간이 10분(600초)을 초과하거나, 다시 시작할 때 로그온 화면 표시가 해제(`"0"`)된 경우
  - **안내 문구**:
    - `화면 보호기 대기 시간이 10분을 초과합니다.`
    - `다시 시작할 때 로그온 화면 표시 설정이 되어있지 않습니다.`

## 2. 상태를 만드는 방법 (OS 주입)
- 레지스트리 경로: `HKEY_CURRENT_USER\Control Panel\Desktop`
- 취약 상태 주입:
  - `ScreenSaveActive` (`REG_SZ`): `"1"`
  - `ScreenSaveTimeOut` (`REG_SZ`): `"900"` (15분)
  - `ScreenSaverIsSecure` (`REG_SZ`): `"0"` (잠금 해제)
  - 변경 전 `StateGuard`로 원래 레지스트리 값을 백업하고, 종료 시 원래 값으로 복구

## 3. 조치 시 기대 동작
- 점검결과 화면에서 7번 항목의 `'조치'` 버튼 클릭 시:
  - UI 상태가 `'취약'`에서 `'안전'`으로 변경되고 상단 취약 건수가 1 감소하며 점수가 재계산됨
  - 실제 OS 레지스트리 `ScreenSaveTimeOut`이 `"600"`(10분), `ScreenSaverIsSecure`가 `"1"`로 변경됨

