# 50. 비인가 무선 AP 사용 여부 점검 (`check_50_비인가무선AP`)

- **점검 번호**: 50번
- **점검 제목**: 50. 비인가 무선 AP 사용 여부 점검
- **앱 UI 키워드**: `비인가 무선 AP 사용 여부`
- **자동화 난이도**: Tier C (관리 서버 정책 등록, 하드웨어/OS 버전, 대량 데이터 등 별도 환경 필요)
- **분류 근거**: 관리 서버의 무선 AP 허용 정책 등록 및 PC의 Wi-Fi 알려진 네트워크 프로필 환경이 필요함
- **구현 상태**: `skeleton`
- **pytest 마커**: `check50`, `tier_c`

## 1. 점검 대상 및 판정 기준 / 안내 문구
- **점검 대상**: 비인가 무선 AP 사용 여부 점검
- [itst_office_5G, itst_office_2.4G가 허용 ON 상태] 안전 및 관리자가 허용한 무선 네트워크만을 사용 중입니다. itst_office_5G
- 안전 및 관리자가 허용한 무선 네트워크만을 사용 중입니다. itst_office_2.4G itst_office_5G
- [설정>네트워크 및 인터넷>Wi-Fi>알려진 네트워크 관리에서 itst_office_5G, itst_office_2.4G 등록 상태] 취약 및 관리자가 허용하지 않은 무선 네트워크를 사용한 적이 있습니다. itst_office_2.4G
- 취약 및 관리자가 허용하지 않은 무선 네트워크를 사용한 적이 있습니다. itst_office_2.4G itst_office_5G
- 취약 및 관리자가 허용하지 않은 무선 네트워크를 사용한 적이 있습니다. itst_office_5G

## 2. 상태를 만드는 방법 (OS / 환경 설정)
- (itst_office_5G, itst_office_2.4G가 허용 ON 상태) 설정>네트워크 및 인터넷>Wi-Fi>알려진 네트워크 관리에서 itst_office_5G만 등록 후 점검 진행
- 설정>네트워크 및 인터넷>Wi-Fi>알려진 네트워크 관리에서 itst_office_5G, itst_office_2.4G 등록 후 점검 진행
- (설정>네트워크 및 인터넷>Wi-Fi>알려진 네트워크 관리에서 itst_office_5G, itst_office_2.4G 등록 상태) itst_office_2.4G 허용 OFF>PSI 재부팅>점검 진행
- itst_office_2.4G, itst_office_5G 허용 OFF>PSI 재부팅>점검 진행
- 설정>네트워크 및 인터넷>Wi-Fi>알려진 네트워크 관리에서 itst_office_2.4G 제거 후 점검 진행

## 3. 조치 시 기대 동작
- 별도 자동 조치 버튼 시나리오 없음 (OS 상태 변경 후 재점검 시 상태 전환 및 점수 가감 확인)
- 공통 사항: 취약 상태에서 안전 상태로 전환 시 상단 취약 건수 감소 및 서버 설정 점수 가감 일치 확인
