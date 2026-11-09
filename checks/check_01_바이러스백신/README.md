# 01. 바이러스 백신 설치 및 실행 여부 점검 (`check_01_바이러스백신`)

- **점검 번호**: 1번
- **점검 제목**: 1. 바이러스 백신 설치 및 실행 여부 점검
- **앱 UI 키워드**: `바이러스 백신 설치 및 실행`
- **자동화 난이도**: Tier B (외부 프로그램 설치 또는 PowerShell/권한/재부팅 환경 구성 필요)
- **분류 근거**: V3 Lite, 알약 등 외부 백신 설치·실시간 감시 제어 및 Windows 보안 모달/서버 백신 지정 정책 연동이 필요함
- **구현 상태**: `skeleton`
- **pytest 마커**: `check01`, `tier_b`

## 1. 점검 대상 및 판정 기준 / 안내 문구
- **점검 대상**: 바이러스 백신 설치 및 실행 여부 점검
- [defender: O] 안전 및 Windows Defender 실시간 감시 기능: 켜짐
- [defender: X (windows 보안> 바이러스 및 위협방지> 바이러스 및 위협방지 설정>실시간 감시 켜기)] 취약 및 Windows Defender 실시간 감시 기능: 꺼짐
- Windows 보안 모달 출력
- 안전 및 Windows Defender 실시간 감시 기능: 켜짐
- [v3: O] 안전 및 AhnLab V3 Lite 실시간 감시 기능: 켜짐 Windows Defender 실시간 감시 기능: 꺼짐
- [v3: X] 취약 및 AhnLab V3 Lite 실시간 감시 기능: 꺼짐 Windows Defender 실시간 감시 기능: 꺼짐
- v3 실시간 감지 ON 하는 Windows 보안 모달 오픈
- 안전 및 AhnLab V3 Lite 실시간 감시 기능: 켜짐 Windows Defender 실시간 감시 기능: 꺼짐
- [알약: O] 안전 및 알약 실시간 감시 기능: 켜짐 Windows Defender 실시간 감시 기능: 꺼짐
- [알약: X] 취약 및 알약 실시간 감시 기능: 꺼짐 Windows Defender 실시간 감시 기능: 꺼짐
- Windows 보안 모달 출력
- 안전 및 Windows Defender 실시간 감시 기능: 켜짐 알약 실시간 감시 기능: 꺼짐
- [v3: O 알약: O] 안전 및 알약 실시간 감시 기능: 켜짐 AhnLab V3 Lite 실시간 감시 기능: 켜짐 Windows Defender 실시간 감시 기능: 꺼짐
- [v3: X 알약: O] 안전 및 알약 실시간 감시 기능: 켜짐 AhnLab V3 Lite 실시간 감시 기능: 꺼짐 Windows Defender 실시간 감시 기능: 꺼짐
- [v3: X 알약: X] 안전 및 알약 실시간 감시 기능: 꺼짐 AhnLab V3 Lite 실시간 감시 기능: 꺼짐 Windows Defender 실시간 감시 기능: 꺼짐
- Windows 보안 모달 출력(v3)
- 안전 및 알약 실시간 감시 기능: 꺼짐 AhnLab V3 Lite 실시간 감시 기능: 켜짐 Windows Defender 실시간 감시 기능: 꺼짐
- 취약 및 관리자가 지정한 다음 중 하나의 백신이 설치되어야 합니다. - test

## 2. 상태를 만드는 방법 (OS / 환경 설정)
- (defender: O) 점검 진행
- 바이러스 및 위협 방지 켜기 후 재점검
- (v3: O) v3 설치 후 점검 진행
- (v3: X) v3 실시간 검사 off 후 점검
- v3 on 후 재점검
- (알약: O) 알약 설치 후 점검 진행(v3 설치 안된 pc)
- (알약: X) 알약 실시간 검사 off 후 점검(v3 설치 안된 pc)
- 바이러스 및 위협 방지 켜기 후 재점검
- (v3: O 알약: O) 점검 진행
- v3 실시간 검사 on 후 재점검
- 서버 바이러스 백신 관리에 "test" 등록 후 점검

## 3. 조치 시 기대 동작
- **조치 진행** → Windows 보안 모달 출력
- **조치 진행** → v3 실시간 감지 ON 하는 Windows 보안 모달 오픈
- **조치 진행** → Windows 보안 모달 출력
- **조치 진행** → Windows 보안 모달 출력(v3)
- 공통 사항: 취약 상태에서 안전 상태로 전환 시 상단 취약 건수 감소 및 서버 설정 점수 가감 일치 확인
