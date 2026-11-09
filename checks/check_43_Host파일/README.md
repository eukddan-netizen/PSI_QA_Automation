# 43. Host 파일 사용 여부 점검 (`check_43_Host파일`)

- **점검 번호**: 43번
- **점검 제목**: 43. Host 파일 사용 여부 점검
- **앱 UI 키워드**: `Host 파일 사용 여부`
- **자동화 난이도**: Tier A (레지스트리/net 명령/Windows 기본 설정으로 완전 자동화 가능)
- **분류 근거**: C:\Windows\System32\drivers\etc\hosts 파일 백업·생성·삭제만으로 완전 자동화가 가능함
- **구현 상태**: `skeleton`
- **pytest 마커**: `check43`, `tier_a`

## 1. 점검 대상 및 판정 기준 / 안내 문구
- **점검 대상**: Host 파일 사용 여부 점검
- [C:\Windows\System32\drivers\etc\hosts 파일 x] 취약 및 hosts 파일을 사용 중입니다.
- [hosts 파일 존재] 안전 및 hosts 파일이 존재하지 않습니다. C:\Windows\System32\drivers\etc\hosts 삭제 확인

## 2. 상태를 만드는 방법 (OS / 환경 설정)
- (C:\Windows\System32\drivers\etc\hosts 파일 x) C:\Windows\System32\drivers\etc\hosts 파일 생성 후 점검 진행(알약 종료 필요)
- 수동 삭제 후 재점검 진행

## 3. 조치 시 기대 동작
- **조치 진행** → 안전 및 hosts 파일이 존재하지 않습니다. C:\Windows\System32\drivers\etc\hosts 삭제 확인
- 공통 사항: 취약 상태에서 안전 상태로 전환 시 상단 취약 건수 감소 및 서버 설정 점수 가감 일치 확인
