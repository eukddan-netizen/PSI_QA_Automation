# 36. NTP 시간서버와 자동 동기화 설정 여부 점검 (`check_36_NTP시간동기화`)

- **점검 번호**: 36번
- **점검 제목**: 36. NTP 시간서버와 자동 동기화 설정 여부 점검
- **앱 UI 키워드**: `NTP 시간서버와 자동 동기화`
- **자동화 난이도**: Tier A (레지스트리/net 명령/Windows 기본 설정으로 완전 자동화 가능)
- **분류 근거**: HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 Type(NTP/noSync) 레지스트리로 제어 가능함
- **구현 상태**: `skeleton`
- **pytest 마커**: `check36`, `tier_a`

## 1. 점검 대상 및 판정 기준 / 안내 문구
- **점검 대상**: NTP 시간서버와 자동 동기화 설정 여부 점검
- 안전 및 Windows 시간 서비스가 외부 NTP 서버와 동기화하도록 설정되어 있습니다. HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: NTP
- 취약 및 Windows 시간 서비스가 시간 동기화를 수행하지 않도록 설정되어 있습니다. HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: noSync
- [NoSync 및 시간 안맞는 상태] 안전 및 자동으로 시간 설정: on 상태로 변경 현재 시간으로 시간 동기화 수행된 상태 HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: NTP
- [자동으로 시간 설정: off 상태] 안전 및 자동으로 시간 설정: on 상태로 변경 HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: NTP
- 취약 및 Windows 시간 서비스의 동기화 설정이 올바르지 않습니다. 지원되지 않는 값이 설정되어 있습니다. 날짜 및 시간>자동으로 시간 설정: 상태 변화 x
- [HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: NTP, noSync 이외 랜덤 값] 안전 및 Windows 시간 서비스가 외부 NTP 서버와 동기화하도록 설정되어 있습니다. HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: NTP
- 취약 및 Windows 시간 서비스가 시간 동기화를 수행하지 않도록 설정되어 있습니다. 날짜 및 시간>자동으로 시간 설정: off 상태
- [HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: noSync] 안전 및 Windows 시간 서비스가 외부 NTP 서버와 동기화하도록 설정되어 있습니다. HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: NTP 날짜 및 시간>자동으로 시간 설정: on 상태
- 안전 및 Windows 시간 서비스가 외부 NTP 서버와 동기화하도록 설정되어 있습니다.

## 2. 상태를 만드는 방법 (OS / 환경 설정)
- 날짜 및 시간>자동으로 시간 설정: on 후 점검 진행
- 날짜 및 시간>자동으로 시간 설정: off > 수동으로 현재 시간 아닌 값 설정 후 점검 진행
- HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: NTP, noSync 이외 랜덤 값 설정 후 점검 진행
- HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: noSync 설정 후 점검 진행
- HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: NTP 설정 후 점검 진행

## 3. 조치 시 기대 동작
- **조치 진행** → 안전 및 자동으로 시간 설정: on 상태로 변경 현재 시간으로 시간 동기화 수행된 상태 HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: NTP
- **조치 진행** → 안전 및 자동으로 시간 설정: on 상태로 변경 HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: NTP
- **조치 진행** → 안전 및 Windows 시간 서비스가 외부 NTP 서버와 동기화하도록 설정되어 있습니다. HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: NTP
- **조치 진행** → 안전 및 Windows 시간 서비스가 외부 NTP 서버와 동기화하도록 설정되어 있습니다. HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters의 type 값: NTP 날짜 및 시간>자동으로 시간 설정: on 상태
- 공통 사항: 취약 상태에서 안전 상태로 전환 시 상단 취약 건수 감소 및 서버 설정 점수 가감 일치 확인
