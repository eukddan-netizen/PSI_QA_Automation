# PSI QA Automation (내PC보안점검 QA 자동화)

Windows 기반 사내 보안점검 데스크톱 프로그램(`taKeeper.exe`, ITstation TA-PSI)의 진단 및 조치 정합성을 검증하기 위한 데스크톱 QA 테스트 자동화 프레임워크입니다.

---

## 🚀 주요 특징 및 자동화 돌파 내용

1. **사용자 모니터 데스크톱 자동 전환 (`core/desktop_utils.py`):**
   - 백그라운드 격리 세션에서 실행되는 제약을 해결하기 위해, 사용자의 실제 물리 모니터(`WinSta0\Default`)로 스레드를 전환하여 모니터 화면에 실제 GUI 창을 직접 띄우고 조작합니다.
2. **트레이 아이콘 자동 더블클릭 실행 (`core/app_controller.py`):**
   - 관리자 권한(UAC) 프로세스 제약을 해결하기 위해, 시스템 트레이(DPI 125% 보정)의 보안점검 아이콘을 하드웨어 마우스 레벨로 자동 감지 및 더블클릭하여 창을 무인으로 실행합니다.
3. **프로그램 내부 UI Automation 전수 매핑:**
   - 메인 화면(`▶ 점검 시작`), 점검결과 테이블(663개 요소, 각 항목별 `조치` 버튼, 하단 `재점검` 버튼) 전체를 UIA 트리로 제어합니다.
4. **실제 Windows OS 레지스트리 제어 및 정합성 검증 (`os_handlers/`):**
   - 화면보호기(7번 항목) 등 실제 윈도우 보안 설정을 안전/취약 상태로 강제 주입하고, 프로그램의 진단 및 조치 기능이 정상 동작하는지 OS 레벨에서 검증합니다.

---

## 📁 프로젝트 구조

```text
PSI_QA_Automation/
├── core/
│   ├── app_controller.py       # 보안점검 앱 라이프사이클(트레이 자동 실행, 창 핸들 획득, 종료)
│   └── desktop_utils.py        # 사용자 실제 모니터 데스크톱(Default Desktop) 전환 유틸
├── os_handlers/
│   └── screen_saver.py         # 7번 항목(화면보호기) 레지스트리 조회, 취약/안전 상태 주입 및 검증
├── pages/                      # Page Object Model (점검창 UI 요소)
├── scripts/
│   ├── open_psi_app.py         # 보안점검 창 자동 실행 스크립트
│   ├── run_inspection_start.py # '▶ 점검 시작' 버튼 클릭 테스트
│   ├── scan_all_tabs.py        # 점검결과, 이력, 정리, 설정 전체 화면 UI 스캐너
│   └── scan_app_controls.py    # 메인 화면 컨트롤 스캐너
├── tests/                      # pytest 기반 테스트 시나리오
├── requirements.txt            # 의존성 라이브러리 목록
└── README.md
```

---

## 🛠️ 시작하기

### 1. 가상환경 활성화
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. 보안점검 창 자동 실행 테스트
```powershell
python scripts/open_psi_app.py
```
