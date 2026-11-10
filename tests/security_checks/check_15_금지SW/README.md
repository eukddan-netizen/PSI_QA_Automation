# 15. 금지 SW 설치 여부 점검 (`check_15_금지SW`)

- **점검 번호**: 15번
- **점검 제목**: 15. 금지 SW 설치 여부 점검
- **앱 UI 키워드**: `금지 SW 설치 여부`
- **자동화 난이도**: Tier C (관리 서버 정책 등록, 하드웨어/OS 버전, 대량 데이터 등 별도 환경 필요)
- **분류 근거**: 관리 서버에서 금지 SW(TeamViewer, FileZilla 등) 정책을 등록하고 외부 프로그램 언인스톨러를 제어해야 함
- **구현 상태**: `skeleton`
- **pytest 마커**: `check15`, `tier_c`

## 1. 점검 대상 및 판정 기준 / 안내 문구
- **점검 대상**: 금지 SW 설치 여부 점검
- [금지 sw 정책 x] 안전 및 설치된 금지 소프트웨어가 없습니다.
- [teamviewer 설치 상태] 취약 및 해당 sw명 출력
- [teamviewer 금지 정책] v3 uninstall ui 출력
- [teamviewer uninstall ui 출력] 안전 및 점수 확인
- [teamviewer, DWG FastView 설치 상태] 취약 및 해당 sw명 출력teamviewer, DWG FastView)
- 순서대로 하나씩 uninstall ui 출력 및 삭제
- [teamviewer, DWG FastView, filezilla 설치 상태] 취약 및 해당 sw명 출력(teamviewer, DWG FastView, filezilla)
- 순서대로 하나씩 uninstall ui 출력 및 삭제

## 2. 상태를 만드는 방법 (OS / 환경 설정)
- (금지 sw 정책 x) 점검 진행
- (teamviewer 설치 상태) 서버에서 teamviewer 금지 정책 설정 후 psi 재부팅 후 점검 진행
- (teamviewer uninstall ui 출력) 제거 진행
- (teamviewer, DWG FastView 설치 상태) teamviewer, DWG FastView 금지 정책 후 psi 재부팅 후 점검 진행
- (teamviewer, DWG FastView, filezilla 설치 상태) teamviewer, DWG FastView, filezilla 금지 정책 후 psi 재부팅 후 점검 진행

## 3. 조치 시 기대 동작
- **조치 버튼 클릭>teamviewer 체크>확인** → v3 uninstall ui 출력
- **조치 버튼 클릭>전체 선택>확인** → 순서대로 하나씩 uninstall ui 출력 및 삭제
- **조치 버튼 클릭>전체 선택>확인** → 순서대로 하나씩 uninstall ui 출력 및 삭제
- 공통 사항: 취약 상태에서 안전 상태로 전환 시 상단 취약 건수 감소 및 서버 설정 점수 가감 일치 확인
