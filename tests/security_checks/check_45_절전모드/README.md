# 45. 절전 모드 정책 설정 여부 점검 (`check_45_절전모드`)

- **자동화 난이도**: Tier A (`powercfg` 명령 및 `HKLM\...\PowerSchemes` 레지스트리 검증, 단일 클릭 즉시 조치 가능)
- **구현 상태**: 구현 완료 (`implemented`)
- **마커**: `check45`, `tier_a`

## 1. 점검 대상 및 판정 기준
- **점검 대상**: 전원 연결 시 절전 모드 전환 시간 설정 여부 (`HKLM\SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes\381b4222-f694-41f0-9685-ff5bb260df2e\238c9fa8-0aad-41ed-83f4-97be242c8f20\29f6c1db-86da-48c5-9fdb-f2b67b1f44da`의 `ACSettingIndex`)
- **양호(안전) 기준**:
  - 절전 모드(전원 연결됨)가 30분(`ACSettingIndex: 1800`) 등 일정 시간 후 전환되도록 설정된 경우
  - **안내 문구**: `30분 후 절전 모드로 전환되도록 설정되어 있습니다.`
- **취약 기준**:
  - 절전 모드(전원 연결됨)가 `'안 함'`/`'해당 없음'`(`ACSettingIndex: 0`)으로 설정된 경우
  - **안내 문구**: `절전 모드로 전환되지 않도록 설정되어 있습니다.`

## 2. 상태를 만드는 방법 (OS 주입)
- 명령어: `powercfg /change standby-timeout-ac 0` 실행 시 `ACSettingIndex`가 `0`으로 변경됨
- 변경 전 원래 `ACSettingIndex` 값을 백업하고, 종료 시 `powercfg`로 원래 시간으로 복구

## 3. 조치 시 기대 동작
- 점검결과 화면에서 45번 항목의 `'조치'` 버튼 클릭 시:
  - UI 상태가 `'취약'`에서 `'안전'`으로 변경되고 상단 취약 건수가 1 감소하며 점수가 재계산됨
  - 실제 OS 레지스트리 `ACSettingIndex` 값이 `1800`(30분)으로 변경됨

