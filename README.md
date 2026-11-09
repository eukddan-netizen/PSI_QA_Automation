# PSI QA Automation (내PC보안점검 QA 자동화)

Windows 기반 보안점검 프로그램(`taKeeper.exe`, ITstation TA-PSI)의 진단 및 조치 정합성을 검증하기 위한 데스크톱 QA 테스트 자동화 프레임워크입니다.

## 아키텍처 및 핵심 원리
1. **WebView2 UI 제어 (Playwright over CDP):**
   - 프로그램(`taKeeper.exe`)의 내부 렌더링 엔진인 WebView2에 원격 디버깅 포트(`9222`)를 연결하여, 안정적이고 정밀한 UI 제어(버튼 클릭, 점검 상태 및 리스트 검증)를 수행합니다.
2. **Windows OS 환경 제어 및 검증 (`os_handlers`):**
   - 윈도우 레지스트리(`winreg`), 로컬 보안 정책, PowerShell 등을 직접 조작하여 실제 보안 설정(화면보호기, 패스워드 정책 등)의 취약/안전 상태를 주입하고 검증합니다.
3. **정합성 테스트 (`pytest`):**
   - [OS 취약 상태 주입] → [프로그램 점검] → [UI 결과 검증] → [조치 버튼 클릭] → [실제 OS 변경 여부 검증]의 전 과정을 자동화합니다.

## 프로젝트 구조
```text
PSI_QA_Automation/
├── core/
│   ├── app_controller.py       # taKeeper.exe 실행, 관리자 권한(UAC) 및 WebView2 CDP 연결
│   └── ...
├── os_handlers/
│   ├── screen_saver.py         # 7번 항목(화면보호기) 레지스트리 조회 및 상태 주입
│   └── ...
├── pages/                      # Page Object Model (점검창 UI 요소)
├── scripts/
│   └── inspect_webview.py      # WebView2 DOM 구조 및 컨트롤 진단 스크립트
├── tests/                      # pytest 기반 테스트 케이스
├── requirements.txt
└── README.md
```

## 시작하기

### 1. 가상환경 활성화 및 패키지 설치
```powershell
# 가상환경 활성화
.\.venv\Scripts\Activate.ps1

# 패키지 설치 (기본 설치 완료됨)
pip install -r requirements.txt
```

### 2. UI 요소 탐색 및 진단 실행
```powershell
python scripts/inspect_webview.py
```
