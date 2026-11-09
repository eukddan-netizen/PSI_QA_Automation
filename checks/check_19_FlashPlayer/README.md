# 19. Adobe Flash Player 설치 여부 점검 (`check_19_FlashPlayer`)

- **점검 번호**: 19번
- **점검 제목**: 19. Adobe Flash Player 설치 여부 점검
- **앱 UI 키워드**: `Adobe Flash Player 설치 여부`
- **자동화 난이도**: Tier B (외부 프로그램 설치 또는 PowerShell/권한/재부팅 환경 구성 필요)
- **분류 근거**: Windows 7 호환성 모드로 구버전 Flash Player를 설치하고 설정 앱/언인스톨러로 수동 삭제해야 함
- **구현 상태**: `skeleton`
- **pytest 마커**: `check19`, `tier_b`

## 1. 점검 대상 및 판정 기준 / 안내 문구
- **점검 대상**: Adobe Flash Player 설치 여부 점검
- [미설치] 안전 및 Flash Player가 설치되어 있지 않습니다.
- 취약 및 해당 Flash Player 버전 정보 출력(32.0.0.363)
- [Flash Player 설치 상태] 설정>설치된 앱 ui 출력(수동 삭제 필요)
- 안전 및 Flash Player가 설치되어 있지 않습니다.

## 2. 상태를 만드는 방법 (OS / 환경 설정)
- (미설치) 점검 진행
- 다운로드>파일 우클릭>호환성>호환 모드 windows 7>실행 후 점검 진행
- 수동 삭제 진행 후 재점검(uninstaller 실행)

## 3. 조치 시 기대 동작
- **조치 버튼 클릭** → 설정>설치된 앱 ui 출력(수동 삭제 필요)
- 공통 사항: 취약 상태에서 안전 상태로 전환 시 상단 취약 건수 감소 및 서버 설정 점수 가감 일치 확인
