# 31. Guest 계정 사용 여부 점검 (`check_31_Guest계정`)

- **자동화 난이도**: Tier A (`net user` 명령어 제어 및 단일 클릭 즉시 조치 가능)
- **구현 상태**: 구현 완료 (`implemented`)
- **마커**: `check31`, `tier_a`

## 1. 점검 대상 및 판정 기준
- **점검 대상**: Windows 로컬 `Guest` 계정 활성화 여부 (`컴퓨터 관리 > 로컬 사용자 및 그룹 > 사용자 > Guest`)
- **양호(안전) 기준**:
  - `Guest` 계정이 비활성화(`계정 사용 안 함` 체크, `net user Guest /active:no`)된 경우
  - **안내 문구**: `Guest 계정은 비활성화되어 있습니다.`
- **취약 기준**:
  - `Guest` 계정이 활성화(`계정 사용 안 함` 체크 해제, `net user Guest /active:yes`)된 경우
  - **안내 문구**: `Guest 계정이 활성화되어 있습니다.`

## 2. 상태를 만드는 방법 (OS 주입)
- 명령어: `net user Guest /active:yes` (취약) / `net user Guest /active:no` (안전)
- 변경 전 `StateGuard.set_user_active("Guest", True)`로 원래 활성 상태를 백업하고, 종료 시 원래 상태로 복구

## 3. 조치 시 기대 동작
- 점검결과 화면에서 31번 항목의 `'조치'` 버튼 클릭 시:
  - UI 상태가 `'취약'`에서 `'안전'`으로 변경되고 상단 취약 건수가 1 감소하며 점수가 재계산됨
  - 실제 OS의 `Guest` 계정이 비활성화(`계정 활성: 아니요`) 상태로 변경됨

