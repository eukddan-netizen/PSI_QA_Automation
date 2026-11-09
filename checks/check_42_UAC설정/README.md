# 42. 사용자 계정 컨트롤(UAC) 설정 여부 점검 (`check_42_UAC설정`)

- **점검 번호**: 42번
- **점검 제목**: 42. 사용자 계정 컨트롤(UAC) 설정 여부 점검
- **앱 UI 키워드**: `사용자 계정 컨트롤(UAC)`
- **자동화 난이도**: Tier A (레지스트리/net 명령/Windows 기본 설정으로 완전 자동화 가능)
- **분류 근거**: HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System 레지스트리(ConsentPromptBehaviorAdmin 등)로 제어 가능함
- **구현 상태**: `skeleton`
- **pytest 마커**: `check42`, `tier_a`

## 1. 점검 대상 및 판정 기준 / 안내 문구
- **점검 대상**: 사용자 계정 컨트롤(UAC) 설정 여부 점검
- 취약 및 사용자 계정 컨트롤(UAC) 프롬프트가 일반 데스크톱에서 표시되도록 설정되어 있습니다. ConsentPromptBehaviorAdmin: 0, EnableLUA: 1, PromptOnSecureDesktop: 0
- [UAC 1단계 상태] 안전 및 비 Windows 이진 파일 실행 시 보안 데스크톱에서 동의 또는 거부를 선택하는 프롬프트가 표시됩니다. <3단계> ConsentPromptBehaviorAdmin: 5, EnableLUA: 1, PromptOnSecureDesktop: 1
- 취약 및 사용자 계정 컨트롤(UAC) 프롬프트가 일반 데스크톱에서 표시되도록 설정되어 있습니다. ConsentPromptBehaviorAdmin: 5, EnableLUA: 1, PromptOnSecureDesktop: 0
- [UAC 2단계 상태] 안전 및 비 Windows 이진 파일 실행 시 보안 데스크톱에서 동의 또는 거부를 선택하는 프롬프트가 표시됩니다. <3단계> ConsentPromptBehaviorAdmin: 5, EnableLUA: 1, PromptOnSecureDesktop: 1
- 안전 및 관리자 권한 요청 시 보안 데스크톱에서 동의 또는 거부를 선택하는 프롬프트가 표시됩니다. <4단계> ConsentPromptBehaviorAdmin: 2, EnableLUA: 1, PromptOnSecureDesktop: 1

## 2. 상태를 만드는 방법 (OS / 환경 설정)
- 사용자 계정 컨트롤 설정 변경>1단계 설정 후 점검 진행
- 사용자 계정 컨트롤 설정 변경>2단계 설정 후 점검 진행
- 사용자 계정 컨트롤 설정 변경>3단계 설정 후 점검 진행
- 사용자 계정 컨트롤 설정 변경>4단계 설정 후 점검 진행

## 3. 조치 시 기대 동작
- **조치 진행** → 안전 및 비 Windows 이진 파일 실행 시 보안 데스크톱에서 동의 또는 거부를 선택하는 프롬프트가 표시됩니다. <3단계> ConsentPromptBehaviorAdmin: 5, EnableLUA: 1, PromptOnSecureDesktop: 1
- **조치 진행** → 안전 및 비 Windows 이진 파일 실행 시 보안 데스크톱에서 동의 또는 거부를 선택하는 프롬프트가 표시됩니다. <3단계> ConsentPromptBehaviorAdmin: 5, EnableLUA: 1, PromptOnSecureDesktop: 1
- 공통 사항: 취약 상태에서 안전 상태로 전환 시 상단 취약 건수 감소 및 서버 설정 점수 가감 일치 확인
