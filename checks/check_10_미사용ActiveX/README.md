# 10. 미사용(3개월) ActiveX 프로그램 존재 여부 점검 (`check_10_미사용ActiveX`)

- **점검 번호**: 10번
- **점검 제목**: 10. 미사용(3개월) ActiveX 프로그램 존재 여부 점검
- **앱 UI 키워드**: `미사용(3개월) ActiveX`
- **자동화 난이도**: Tier B (외부 프로그램 설치 또는 PowerShell/권한/재부팅 환경 구성 필요)
- **분류 근거**: PowerShell 스크립트로 System32/SysWOW64 가상 DLL 생성 및 32/64비트 CLSID·IE 사용 통계 바이너리 시간 주입이 필요함
- **구현 상태**: `skeleton`
- **pytest 마커**: `check10`, `tier_b`

## 1. 점검 대상 및 판정 기준 / 안내 문구
- **점검 대상**: 미사용(3개월) ActiveX 프로그램 존재 여부 점검
- 취약 및 3개월 이상 사용하지 않은 ActiveX가 있습니다. Target_QA_2nd_Blind_ActiveX 테스트 스크립트 돌려서 결과 확인 [ O ] 파일 존재함: C:\Windows\SysWOW64\blind_test_activex.dll [ O ] 레지 잔존 (Wow6432Node 배포 유닛 경로) [ O ] 레지 잔존 (Ext\Stats 경로) [ O ] 레지 잔존 (Wow6432Node CLSID 경로)
- [취약 및 Target_QA_2nd_Blind_ActiveX 검출 상태] 안전 및 3개월 이상 사용하지 않은 ActiveX가 없습니다. 기대 결과 메모의 스크립트 돌려서 결과 확인 [ X ] 파일 삭제됨: C:\Windows\SysWOW64\blind_test_activex.dll [ O ] 레지 잔존 (Wow6432Node 배포 유닛 경로) [ X ] 레지 지워짐 (Ext\Stats 경로) [ X ] 레지 지워짐 (Wow6432Node CLSID 경로)
- 취약 및 3개월 이상 사용하지 않은 ActiveX가 있습니다. Target_QA_4th_Blind_ActiveX 테스트 스크립트 돌려서 결과 확인 [ O ] 64비트 파일 존재함: System32\4th_blind_activex.dll [ O ] 32비트 파일 존재함: SysWOW64\4th_blind_activex.dll -------------------------------------------------- [ O ] 레지 잔존 (64비트 배포 유닛) [ O ] 레지 잔존 (64비트 CLSID) ------------------------------------------------- [ O ] 레지 잔존 (32비트 Wow6432Node 배포 유닛) [ O ] 레지 잔존 (32비트 Wow6432Node CLSID) -------------------------------------------------- [ O ] 레지 잔존 (Ext\Stats 통계 경로)
- [취약 및 Target_QA_4th_Blind_ActiveX 검출 상태] 안전 및 3개월 이상 사용하지 않은 ActiveX가 없습니다. 기대 결과 메모의 스크립트 돌려서 결과 확인 [ O ] 64비트 파일 존재함: System32\4th_blind_activex.dll [ X ] 32비트 파일 삭제됨: SysWOW64\4th_blind_activex.dll -------------------------------------------------- [ O ] 레지 잔존 (64비트 배포 유닛) [ O ] 레지 잔존 (64비트 CLSID) -------------------------------------------------- [ O ] 레지 잔존 (32비트 Wow6432Node 배포 유닛) [ X ] 레지 지워짐 (32비트 Wow6432Node CLSID) -------------------------------------------------- [ X ] 레지 지워짐 (Ext\Stats 통계 경로)

## 2. 상태를 만드는 방법 (OS / 환경 설정)
- <powershell 관리자 권한으로 실행 후 스크립트(메모) 실행> 1행 (변수 정의): 테스트용 ActiveX 이름, GUID, 32비트 파일 경로(SysWOW64) 선언. 2행 (파일 생성): 가상 ActiveX 구동 파일(blind_test_activex.dll) 자동 생성. 3행 (통계 주입): Wow6432Node 배포 등록 및 IE 통계에 '25년 1월 1일' 바이너리 시간 기록. 4행 (CLSID 등록): 32비트 CLSID 구조 생성 및 파일 경로 최종 매핑 후 완료 알림. 점검 진행
- <powershell 관리자 권한으로 실행 후 스크립트(메모) 실행> 1행 (변수 정의): 테스트용 ActiveX 이름, GUID, 32비트/64비트 각각의 가상 파일 경로(System32 및 SysWOW64) 선언. 2행 (파일 생성): 64비트 방(System32)과 32비트 방(SysWOW64)에 각각 독립된 가상 ActiveX 구동 파일(.dll) 자동 생성. 3행 (64비트 레지스트리 주입): 64비트 표준 경로의 배포 데이터베이스(Code Store) 등록 및 CLSID 구조 생성 후 64비트 파일 경로 매핑. 4행 (32비트 레지스트리 주입): 32비트 격리 경로(Wow6432Node)의 배포 데이터베이스 등록 및 CLSID 구조 생성 후 32비트 파일 경로 매핑. 5행 (통계 주입): 브라우저 공통 인식 및 가상화 체크를 위한 IE 통계(HKCU)에 바이너리 시간 정보 기록 후 완료 알림.

## 3. 조치 시 기대 동작
- **조치>Target_QA_2nd_Blind_ActiveX 체크>확인** → 안전 및 3개월 이상 사용하지 않은 ActiveX가 없습니다. 기대 결과 메모의 스크립트 돌려서 결과 확인 [ X ] 파일 삭제됨: C:\Windows\SysWOW64\blind_test_activex.dll [ O ] 레지 잔존 (Wow6432Node 배포 유닛 경로) [ X ] 레지 지워짐 (Ext\Stats 경로) [ X ] 레지 지워짐 (Wow6432Node CLSID 경로)
- **조치>Target_QA_4th_Blind_ActiveX 체크>확인** → 안전 및 3개월 이상 사용하지 않은 ActiveX가 없습니다. 기대 결과 메모의 스크립트 돌려서 결과 확인 [ O ] 64비트 파일 존재함: System32\4th_blind_activex.dll [ X ] 32비트 파일 삭제됨: SysWOW64\4th_blind_activex.dll -------------------------------------------------- [ O ] 레지 잔존 (64비트 배포 유닛) [ O ] 레지 잔존 (64비트 CLSID) -------------------------------------------------- [ O ] 레지 잔존 (32비트 Wow6432Node 배포 유닛) [ X ] 레지 지워짐 (32비트 Wow6432Node CLSID) -------------------------------------------------- [ X ] 레지 지워짐 (Ext\Stats 통계 경로)
- 공통 사항: 취약 상태에서 안전 상태로 전환 시 상단 취약 건수 감소 및 서버 설정 점수 가감 일치 확인
