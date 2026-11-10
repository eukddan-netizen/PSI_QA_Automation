# 14. 보안 USB 설치 여부 점검 (`check_14_보안USB`)

- **자동화 난이도**: Tier A (파일시스템 `C:\wwcnt` 폴더 제어 및 단일 클릭 즉시 조치 가능)
- **구현 상태**: 구현 완료 (`implemented`)
- **마커**: `check14`, `tier_a`

## 1. 점검 대상 및 판정 기준
- **점검 대상**: 보안 USB 클라이언트(`SafeUSB` 등, `C:\wwcnt` 폴더 및 관련 프로세스) 설치 여부
- **양호(안전) 기준**:
  - `sec_usb` 항목 중 `isProcessRunning = 1` 또는 `isFilePresent = 1` (`C:\wwcnt` 폴더 존재)인 항목이 존재할 때
- **취약 기준**:
  - `C:\wwcnt` 폴더가 삭제되어 `name=SafeUSB`의 `isFilePresent = 0`이고 실행 중인 보안 USB 프로세스도 없을 때

## 2. 상태를 만드는 방법 (OS 주입)
- 기존 `C:\wwcnt` 폴더를 삭제하지 않고 `C:\wwcnt_psi_backup`으로 임시 이름 변경하여 미존재(취약) 상태를 만듦
- 테스트 종료 시(`StateGuard`) 백업해 둔 `C:\wwcnt_psi_backup`을 원래 `C:\wwcnt`로 복원

## 3. 조치 시 기대 동작
- 점검결과 화면에서 14번 항목의 `'조치'` 버튼 클릭 시:
  - UI 상태가 `'취약'`에서 `'안전'`으로 변경되고 상단 취약 건수가 1 감소하며 점수가 재계산됨
  - 스텔스로 `C:\wwcnt` 폴더가 자동 생성되어 `isFilePresent = 1` 조건을 충족함

