# 23. 원격 지원 금지 설정 여부 점검 (`check_23_원격지원금지`)

- **점검 번호**: 23번
- **점검 제목**: 23. 원격 지원 금지 설정 여부 점검
- **앱 UI 키워드**: `원격 데스크톱 설정 여부`
- **자동화 난이도**: Tier A (레지스트리/net 명령/Windows 기본 설정으로 완전 자동화 가능)
- **분류 근거**: HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server의 fDenyTSConnections 레지스트리로 제어 및 즉시 조치가 가능함
- **구현 상태**: `skeleton`
- **pytest 마커**: `check23`, `tier_a`

## 1. 점검 대상 및 판정 기준 / 안내 문구
- **점검 대상**: 원격 지원 금지 설정 여부 점검
- 안전 및 원격 데스크톱 연결이 거부됩니다. 즉, 이 시스템에 원격으로 연결하는 것이 불가능합니다. HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server의 fDenyTSConnections: 1
- 취약 및 원격 데스크톱 연결이 허용됩니다. 즉, 이 시스템에 원격으로 연결할 수 있습니다. HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server의 fDenyTSConnections: 0
- [취약] 안전 및 원격 데스크톱 설정 OFF
- 안전 및 원격 데스크톱 연결이 거부됩니다. 즉, 이 시스템에 원격으로 연결하는 것이 불가능합니다. 원격 데스크톱 설정 OFF
- 취약 및 원격 데스크톱 연결이 허용됩니다. 즉, 이 시스템에 원격으로 연결할 수 있습니다. 원격 데스크톱 설정 ON
- [fDenyTSConnections: 1이외의 값] 안전 및 fDenyTSConnections: 1 원격 데스크톱 설정 OFF

## 2. 상태를 만드는 방법 (OS / 환경 설정)
- 원격 데스크톱 설정 OFF 후 점검 진행
- 원격 데스크톱 설정 ON 후 점검 진행
- HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server의 fDenyTSConnections: 1 점검 진행
- HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server의 fDenyTSConnections: 0 점검 진행

## 3. 조치 시 기대 동작
- **조치 진행** → 안전 및 원격 데스크톱 설정 OFF
- **조치 진행** → 안전 및 fDenyTSConnections: 1 원격 데스크톱 설정 OFF
- 공통 사항: 취약 상태에서 안전 상태로 전환 시 상단 취약 건수 감소 및 서버 설정 점수 가감 일치 확인
