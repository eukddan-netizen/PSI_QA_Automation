# 28. 유해 ActiveX 설치 여부 점검 (`check_28_유해ActiveX`)

- **점검 번호**: 28번
- **점검 제목**: 28. 유해 ActiveX 설치 여부 점검
- **앱 UI 키워드**: `유해 ActiveX 설치 여부`
- **자동화 난이도**: Tier C (관리 서버 정책 등록, 하드웨어/OS 버전, 대량 데이터 등 별도 환경 필요)
- **분류 근거**: PowerShell 가상 ActiveX 주입 후 관리 서버에서 유해 ActiveX 정책 및 예외 정책을 설정해야 함
- **구현 상태**: `skeleton`
- **pytest 마커**: `check28`, `tier_c`

## 1. 점검 대상 및 판정 기준 / 안내 문구
- **점검 대상**: 유해 ActiveX 설치 여부 점검
- 테스트 pc의 sw 목록>Target_QA_2nd_Blind_ActiveX 설치 확인
- [Target_QA_2nd_Blind_ActiveX 설치 상태] 취약 및 해로운 ActiveX가 설치되어 있습니다. Target_QA_2nd_Blind_ActiveX
- [Target_QA_2nd_Blind_ActiveX 유해 및 취약 상태] 안전 및 해로운 ActiveX가 설치되어 있지 않습니다. 검증 스크립트 확인
- 안전 및 해로운 ActiveX가 설치되어 있지 않습니다.

## 2. 상태를 만드는 방법 (OS / 환경 설정)
- <powershell 관리자 권한으로 실행 후 스크립트(메모) 실행> 1행 (변수 정의): 테스트용 ActiveX 이름, GUID, 32비트 파일 경로(SysWOW64) 선언. 2행 (파일 생성): 가상 ActiveX 구동 파일(blind_test_activex.dll) 자동 생성. 3행 (통계 주입): Wow6432Node 배포 등록 및 IE 통계에 '25년 1월 1일' 바이너리 시간 기록. 4행 (CLSID 등록): 32비트 CLSID 구조 생성 및 파일 경로 최종 매핑 후 완료 알림. 에이전트 재시작
- (Target_QA_2nd_Blind_ActiveX 설치 상태) 해당 테스트 pc에 Target_QA_2nd_Blind_ActiveX 유해 정책 설정 후 점검 진행(에이전트 실행 주기 후 동작)
- 보안점검>예외설정>ActiveX예외에 Target_QA_2nd_Blind_ActiveX 등록>psi재부팅 후 점검 진행

## 3. 조치 시 기대 동작
- **조치>Target_QA_2nd_Blind_ActiveX 체크>확인** → 안전 및 해로운 ActiveX가 설치되어 있지 않습니다. 검증 스크립트 확인
- 공통 사항: 취약 상태에서 안전 상태로 전환 시 상단 취약 건수 감소 및 서버 설정 점수 가감 일치 확인
