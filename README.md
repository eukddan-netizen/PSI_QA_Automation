# topAegis 내PC보안점검 (TA-PSI) UI 자동화

Windows 데스크톱 보안점검 프로그램(`taKeeper.exe`, CefSharp 임베디드 웹뷰 기반)의 **53개 보안점검 항목**을 무인으로 테스트하고 정합성을 검증하는 Python + pytest 기반 UI 자동화 프로젝트입니다.

---

## 1. 빠른 실행 방법 (Quick Start)

프로젝트 루트(`d:\psi_automation`) 터미널에서 **점검 번호만 입력**하여 즉시 테스트를 실행할 수 있습니다.

### 점검별 단축 실행
```powershell
# 14번 보안 USB 점검 실행
.\run 14

# 7번 화면보호기 점검 실행
.\run 7

# 45번 절전 모드 점검 실행
.\run 45

# 현재 구현된 시범 점검(7, 14, 45번) 한 번에 실행
.\run pilot

# 프로그램 자체 UI/기능 점검(app_checks) 전체 실행
.\run app

# 전체 점검 및 테스트 목록 확인
.\run list
```

> **Tip (앞에 `.\`도 빼고 그냥 `run 14`로 치고 싶을 때)**  
> PowerShell 터미널에 아래 명령을 딱 한 번 입력해 두시면, 해당 창에서는 `run 14`만 쳐도 바로 실행됩니다.
> ```powershell
> function run { .\run.ps1 $args }
> ```

<details>
<summary><b>기존 pytest 명령어로 직접 실행하기 (펼치기)</b></summary>

```powershell
# 특정 마커 실행 (-s: 실시간 로그 출력)
.\.venv\Scripts\pytest.exe -m check14 -s

# Tier A 난이도 점검 전체 실행
.\.venv\Scripts\pytest.exe -m tier_a -s

# 전체 점검 테스트 수집 확인
.\.venv\Scripts\pytest.exe --collect-only
```
</details>

---

## 2. 프로젝트 소개

본 프로젝트는 보안점검 프로그램의 모든 진단 항목을 대상으로 **"OS 취약 주입부터 조치 후 OS 정합성 검증, 그리고 안전 원복까지"** 전 과정을 사람의 개입 없이 100% 무인 자동화(E2E)로 검증합니다.

### 핵심 자동화 사이클 (모든 점검 동일 적용)
1. **준비 (Backup & Inject)**: 변경 전 사용자의 원래 OS 설정(레지스트리/계정/폴더 등)을 백업하고, 테스트할 **취약 상태**를 OS에 강제 주입
2. **실행 (Auto Launch & Scan)**: 시스템 트레이 아이콘을 자동 더블클릭하여 앱을 물리 화면에 띄우고, **'점검 시작'** 클릭 및 점검 완료 대기
3. **검증 (Verify UI)**: '점검결과' 화면에서 해당 점검의 **'취약'** 판정과 조치 전 점수/취약 건수 확인
4. **조치 (Remediate & Assert)**: **'조치'** 버튼 클릭 후 실시간 **'안전'** 전환, 취약 건수 감소(-1) 및 점수 가감 확인, 실제 **Windows OS 값 변경 정합성** 검증
5. **원복 (Guaranteed Teardown)**: 테스트가 성공하든 중간에 실패하든 상관없이, 종료 시 `StateGuard`가 PC 설정을 **원래 상태로 100% 자동 복구**

---

## 3. 프로젝트 폴더 구조

다음 릴리즈에서 점검이 추가/삭제되거나 번호가 바뀌어도 **해당 점검 폴더만 수정**하면 되고, 다른 점검이나 공통 코드는 건드릴 필요가 없는 완전 독립 모듈 구조로 설계되었습니다.

```text
d:\psi_automation/
├─ tests/                          # 전체 테스트 스위트 (단일 상위 폴더)
│  ├─ security_checks/             # 53개 보안점검 항목별 독립 모듈 (check_01 ~ check_53)
│  │  ├─ catalog.yaml              # 53개 전체 보안점검 카탈로그 (번호, 이름, UI키워드, Tier)
│  │  ├─ check_01_바이러스백신/
│  │  │  ├─ handler.py             # 점검 전용 OS 상태 제어 (set_vulnerable, set_secure, is_secure)
│  │  │  ├─ test_check_01.py       # pytest 테스트 실행 코드
│  │  │  └─ README.md              # 엑셀 기반 판정 기준, 안내 문구, 조치 동작 명세서
│  │  ├─ check_07_화면보호기/       # [구현/통과] HKCU 레지스트리 기반 점검
│  │  ├─ check_14_보안USB/         # [구현/통과] 로컬 파일시스템(C:\wwcnt) 기반 점검
│  │  ├─ check_31_Guest계정/       # [구현] net user Guest 명령 기반 점검 (관리자 권한 시 실행)
│  │  ├─ check_40_널세션접근제어/   # [구현] HKLM 시스템 보안 레지스트리 기반 점검 (관리자 권한 시 실행)
│  │  ├─ check_45_절전모드/         # [구현/통과] powercfg 명령 및 HKLM PowerSchemes 레지스트리 기반
│  │  └─ ... (check_01 ~ check_53 총 53개 폴더)
│  │
│  └─ app_checks/                  # 프로그램 자체 UI 및 기능 점검 (엑셀 69릴리즈 9~71행 기반)
│     ├─ catalog_app.yaml          # 7개 앱 기능 카탈로그 (트레이, 대시보드, 점검, 이력, 정리, 설정, 결과)
│     ├─ 01_tray_menu/             # [Row 9~19] 트레이 우클릭 메뉴 및 사용자정보 웹뷰 유효성 검증
│     ├─ 02_main_dashboard/        # [Row 20~34] 메인 대시보드 방패/경고팝업, 지표 hover, 도움말/암호 모달
│     ├─ 03_inspection_run/        # [Row 35~37] 점검 진행 프로그레스바(100%) 및 탭 자동 전환
│     ├─ 04_history/               # [Row 38~47] 점검이력 아코디언 토글 및 엑셀 내보내기/정합성 검증
│     ├─ 05_pc_clean/              # [Row 48~58] OS버전/백신/방화벽 동기화, 임시파일/브라우저캐시 실제 삭제
│     ├─ 06_settings/              # [Row 59~65] 결과이동 옵션 해제 팝업, 다크/라이트 테마 및 버전 정보
│     └─ 07_result_common/         # [Row 66~71] 결과화면 방패/카운트 무결성, 컬럼 헤더 정렬 검증
│
├─ common/                      # 전 점검 공통 인프라
│  ├─ os_utils.py               # 레지스트리/명령어 제어, StateGuard 원복 가드, 동적 핸들러 로더
│  └─ check_harness.py          # 5단계 표준 점검 테스트 흐름 공통 실행기
│
├─ pages/                       # CefSharp 크롬 웹뷰 UI Automation Page Object
│  ├─ main_page.py              # 메인 화면 전환, '▶ 점검 시작' 클릭 및 진행 대기
│  └─ inspection_result_page.py # 점검번호/키워드 행 탐색, 조치 클릭, 취약 카운트/점수 가감 검증
│
├─ core/                        # 데스크톱 환경 제어
│  ├─ app_controller.py         # 백그라운드 프로세스 정리 및 시스템 트레이 더블클릭 무인 실행
│  └─ desktop_utils.py          # 사용자 물리 화면('Default' Desktop) 세션 스레드 전환
│
├─ tools/
│  └─ uia_dump.py               # 현재 열린 내PC보안점검 창의 모든 UIA 요소를 파일/콘솔로 덤프
│
├─ run.bat / run.ps1            # 번호만 입력해 점검을 즉시 실행하는 단축 러너 스크립트
├─ conftest.py                  # 실패 시에도 원복을 100% 보장하는 state_guard fixture
├─ pytest.ini                   # importlib 격리 모드 및 점검별(check01~check53)/Tier별 마커 정의
└─ requirements.txt             # 의존성 라이브러리 목록 (pywinauto, pyyaml 등)
```

---

## 4. 53개 점검 난이도(Tier) 분류 현황

모든 점검의 메타데이터와 분류 근거는 [`tests/security_checks/catalog.yaml`](tests/security_checks/catalog.yaml)에 등록되어 있습니다.

| 난이도 분류 | 개수 | 점검 번호 | 설명 및 구현 우선순위 |
| :---: | :---: | :--- | :--- |
| **Tier A** | **22개** | `07, 08, 14, 17, 21, 22, 23, 25, 30, 31, 32, 33, 36, 37, 38, 40, 42, 43, 45, 46, 47, 48` | 레지스트리, net/powercfg/netsh 명령, 파일 제어만으로 외부 의존성 없이 **완전 자동화 가능** (최우선 구현) |
| **Tier B** | **15개** | `01, 02, 03, 04, 05, 06, 10, 11, 12, 18, 19, 20, 24, 26, 35` | 외부 프로그램(V3, 알약, 한글, Acrobat, Office, Java 등) 설치, PowerShell 가상 DLL 주입, VHD 마운트, OS 재부팅 필요 |
| **Tier C** | **13개** | `13, 15, 27, 28, 29, 39, 41, 44, 49, 50, 51, 52, 53` | 관리 서버 정책(금지/유해 SW, 신뢰 사이트, 인가 DNS, 방화벽 IP 500개 등) 등록 또는 하드웨어/OS 빌드 의존 |
| **제외** | **3개** | `09, 16, 34` | 수동만 가능하거나 테스트 시나리오가 사실상 없는 항목 (시나리오 공란, 정상 OS에서 상시 안전 등) |

---

## 5. 점검 개편 시 유지보수 방법

향후 보안점검 대규모 개편으로 점검 번호나 명칭, 로직이 바뀌더라도 다른 코드는 건드릴 필요가 없습니다.

1. **점검 번호/이름이 바뀔 때**: `checks/catalog.yaml`의 해당 항목과 해당 점검 폴더명(`checks/check_NN_이름/`), `test_check_NN.py`의 번호만 변경
2. **판정 기준이나 OS 레지스트리/명령이 바뀔 때**: 해당 점검 폴더 안의 `handler.py`와 `README.md`만 수정
3. **신규 점검 추가**: `checks/check_NN_이름/` 폴더를 만들고 `handler.py`, `test_check_NN.py`, `README.md`를 작성한 뒤 `catalog.yaml`에 1줄 등록
