# 32. Administrator 계정 사용 여부 점검 (`check_32_Administrator계정`)

- **점검 번호**: 32번
- **점검 제목**: 32. Administrator 계정 사용 여부 점검
- **앱 UI 키워드**: `Administrator 계정 사용 여부`
- **자동화 난이도**: Tier A (레지스트리/net 명령/Windows 기본 설정으로 완전 자동화 가능)
- **분류 근거**: net user Administrator /active:yes|no 명령만으로 상태를 제어하고 단일 클릭 조치를 검증할 수 있음
- **구현 상태**: `skeleton`
- **pytest 마커**: `check32`, `tier_a`

## 1. 점검 대상 및 판정 기준 / 안내 문구
- **점검 대상**: Administrator 계정 사용 여부 점검
- 안전 및 Administrator 계정은 비활성화되어 있습니다.
- 취약 및 Administrator 계정이 활성화되어 있습니다.
- [Administrator 계정 활성화 상태] 안전 및 Administrator계정은 비활성화되어 있습니다. 컴퓨터 관리>로컬 사용자 및 그룹>사용자>Administrator: "사용 안 함" 체크 상태

## 2. 상태를 만드는 방법 (OS / 환경 설정)
- 컴퓨터 관리>로컬 사용자 및 그룹>사용자>Administrator: "사용 안 함" 체크 -> 점검 진행
- 컴퓨터 관리>로컬 사용자 및 그룹>사용자>Administrator: "사용 안 함" uncheck -> 점검 진행

## 3. 조치 시 기대 동작
- **조치 진행** → 안전 및 Administrator계정은 비활성화되어 있습니다. 컴퓨터 관리>로컬 사용자 및 그룹>사용자>Administrator: "사용 안 함" 체크 상태
- 공통 사항: 취약 상태에서 안전 상태로 전환 시 상단 취약 건수 감소 및 서버 설정 점수 가감 일치 확인
