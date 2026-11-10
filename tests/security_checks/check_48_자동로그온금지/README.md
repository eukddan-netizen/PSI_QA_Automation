# 48. 윈도우 자동 로그온 금지 설정 여부 점검 (`check_48_자동로그온금지`)

- **점검 번호**: 48번
- **점검 제목**: 48. 윈도우 자동 로그온 금지 설정 여부 점검
- **앱 UI 키워드**: `윈도우 자동 로그온 금지`
- **자동화 난이도**: Tier A (레지스트리/net 명령/Windows 기본 설정으로 완전 자동화 가능)
- **분류 근거**: HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon의 AutoAdminLogon 레지스트리(1 vs 0)로 제어 가능함
- **구현 상태**: `skeleton`
- **pytest 마커**: `check48`, `tier_a`

## 1. 점검 대상 및 판정 기준 / 안내 문구
- **점검 대상**: 윈도우 자동 로그온 금지 설정 여부 점검
- 취약 및 사용자 이름과 암호를 입력할 필요 없이 자동으로 로그인 되도록 설정되어 있습니다. HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon의 AutoAdminLogon 변수 생성 + 값: 1
- [실행 > netplwiz > '사용자 이름과 암호를 입력해야 이 컴퓨터를 사용할 수 있음' unCheck 상태] 안전 및 사용자 이름과 암호를 입력해야 이 컴퓨터를 사용할 수 있도록 안전하게 설정되어 있습니다. 실행 > netplwiz > '사용자 이름과 암호를 입력해야 이 컴퓨터를 사용할 수 있음' 체크 상태 HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon의 AutoAdminLogon 값: 0
- 안전 및 사용자 이름과 암호를 입력해야 이 컴퓨터를 사용할 수 있도록 안전하게 설정되어 있습니다. HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon의 AutoAdminLogon 값: 1
- 취약 및 사용자 이름과 암호를 입력할 필요 없이 자동으로 로그인 되도록 설정되어 있습니다. 실행 > netplwiz > '사용자 이름과 암호를 입력해야 이 컴퓨터를 사용할 수 있음' unCheck 상태
- 안전 및 사용자 이름과 암호를 입력해야 이 컴퓨터를 사용할 수 있도록 안전하게 설정되어 있습니다. 실행 > netplwiz > '사용자 이름과 암호를 입력해야 이 컴퓨터를 사용할 수 있음' 체크 상태

## 2. 상태를 만드는 방법 (OS / 환경 설정)
- 실행 > netplwiz > '사용자 이름과 암호를 입력해야 이 컴퓨터를 사용할 수 있음' unCheck 후 점검 진행
- 실행 > netplwiz > '사용자 이름과 암호를 입력해야 이 컴퓨터를 사용할 수 있음' 체크 선택 후 재점검
- HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon의 AutoAdminLogon 값: 1 설정 후 점검 진행
- HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon의 AutoAdminLogon 값: 0 설정 후 점검 진행

## 3. 조치 시 기대 동작
- **조치 진행** → 안전 및 사용자 이름과 암호를 입력해야 이 컴퓨터를 사용할 수 있도록 안전하게 설정되어 있습니다. 실행 > netplwiz > '사용자 이름과 암호를 입력해야 이 컴퓨터를 사용할 수 있음' 체크 상태 HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon의 AutoAdminLogon 값: 0
- 공통 사항: 취약 상태에서 안전 상태로 전환 시 상단 취약 건수 감소 및 서버 설정 점수 가감 일치 확인
