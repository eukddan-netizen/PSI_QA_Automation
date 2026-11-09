# 40. 비인가된 사용자의 널(Null) 세션 접근 제어 설정 여부 점검 (`check_40_널세션접근제어`)

- **자동화 난이도**: Tier A (`HKLM` 보안 정책 레지스트리 제어 및 단일 클릭 즉시 조치 가능)
- **구현 상태**: 구현 완료 (`implemented`)
- **마커**: `check40`, `tier_a`

## 1. 점검 대상 및 판정 기준
- **점검 대상**: 로컬 보안 정책 `네트워크 액세스: SAM 계정과 공유의 익명 열거 허용 안 함` (`HKLM\SYSTEM\CurrentControlSet\Control\Lsa`의 `restrictanonymous`)
- **양호(안전) 기준**:
  - `restrictanonymous` (`REG_DWORD`) 값이 `0` 이외의 값(`1` 등, 정책 '사용')인 경우
  - **안내 문구**: `'네트워크 액세스: SAM 계정과 공유의 익명 열거 허용 안 함' 정책이 활성화되어 있습니다.`
- **취약 기준**:
  - `restrictanonymous` (`REG_DWORD`) 값이 `0`(정책 '사용 안 함')인 경우
  - **안내 문구**: `'네트워크 액세스: SAM 계정과 공유의 익명 열거 허용 안 함' 정책이 비활성화되어 있습니다.`

## 2. 상태를 만드는 방법 (OS 주입)
- 레지스트리 경로: `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Lsa`
- 취약 상태 주입: `restrictanonymous` (`REG_DWORD`) = `0`
- 변경 전 `StateGuard`로 원래 `restrictanonymous` 값을 백업하고, 종료 시 원래 값으로 복구

## 3. 조치 시 기대 동작
- 점검결과 화면에서 40번 항목의 `'조치'` 버튼 클릭 시:
  - UI 상태가 `'취약'`에서 `'안전'`으로 변경되고 상단 취약 건수가 1 감소하며 점수가 재계산됨
  - 실제 OS 레지스트리 `HKLM\SYSTEM\CurrentControlSet\Control\Lsa\restrictanonymous` 값이 `1`로 변경됨

