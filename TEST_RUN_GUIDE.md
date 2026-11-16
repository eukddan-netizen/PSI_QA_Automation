# TA-PSI UI 자동화 테스트 실행 가이드

본 문서는 `d:\psi_automation` 프로젝트의 모든 테스트(**프로그램 UI/기능 점검 `app_checks`** 및 **53개 보안점검 `security_checks`**)를 일관된 방식으로 실행하고 필터링하는 방법을 정리한 실행 가이드입니다.

---

## 1. 실행 전 사전 준비

1. **작업 디렉터리**: 프로젝트 루트(`d:\psi_automation`)에서 PowerShell을 엽니다.
2. **가상환경**: `.venv\Scripts\pytest.exe`가 자동으로 사용되므로 별도 `activate` 없이 `.\run` 또는 `.\run.ps1`을 바로 실행할 수 있습니다.
3. **관리자 권한 권장 대상**:
   - 트레이 우클릭 메뉴 중 상위 프로세스(`taAssistant`) 제어가 필요한 항목(`tray 2, 3, 4, 5, 7`)
   - HKLM 레지스트리/시스템 정책을 제어하는 보안점검 항목(`check31`, `check40`, `check45` 등)
   - 권장: **관리자 권한으로 실행한 PowerShell**에서 테스트 실행
4. **단축 명령 설정 (선택)**:
   현재 PowerShell 세션에서 `.\` 없이 `run`만 입력하려면 아래를 1회 실행합니다.
   ```powershell
   function run { .\run.ps1 $args }
   ```

---

## 2. 계층형 단축 실행 구조 (`.\run`)

모든 테스트는 **`대분류(탭 / 영역)` → `중분류(세부 번호)` → `개별 테스트(-k)`** 계층으로 실행할 수 있습니다.

### 2-1. 프로그램 UI/기능 점검 (`tests/app_checks`) — 탭별 대분류 실행 (한글/영문 모두 지원)

| 실행 명령 (한글 / 영문) | 대상 대분류 / 폴더 | pytest 마커 | 비고 |
| :--- | :--- | :--- | :--- |
| `.\run app` | 프로그램 UI/기능 전체 | `app_check` | 전체 탭 일괄 실행 |
| `.\run app list` | 대분류 목록 조회 | - | 탭별 명령어/마커 출력 |
| `.\run 트레이` / `.\run tray` | `01_트레이` (트레이 아이콘) | `app_tray` | 중분류 1~7 전체 |
| `.\run 메인` / `.\run main` | `02_메인` (보안점검 메인 탭) | `app_main` | 중분류 1~7 전체 |
| `.\run 점검` / `.\run inspection` | `03_점검` (점검 탭) | `app_inspection` | 사용자 정보 / 실시간 진행 / 결과 전환 |
| `.\run 점검결과` / `.\run result` | `04_점검결과` (점검결과 탭) | `app_result` | 방패/점수/정책정합성/카운트/정렬 |
| `.\run 점검이력` / `.\run history` | `05_점검이력` (점검이력 탭) | `app_history` | 이력 리스트 / 상세 / 엑셀 내보내기 |
| `.\run PC정리` / `.\run clean` | `06_PC정리` (PC정리 탭) | `app_clean` | OS/백신/방화벽/캐시 정리 |
| `.\run 설정` / `.\run settings` | `07_설정` (설정 탭) | `app_settings` | 일반/외형/정보 |

#### 중분류 / 세부 테스트 필터링 예시
```powershell
# 트레이 아이콘 중분류 목록 확인 및 실행
.\run tray list
.\run tray 1          # tray_01 (내PC보안점검)
.\run tray 1-3        # tray_01 ~ tray_03 연속 실행
.\run tray 2,5        # tray_02, tray_05 선택 실행

# 메인 탭 중분류 목록 확인 및 실행
.\run main list
.\run main 3          # main_03 (사용자 정보)
.\run main 1-2        # main_01 ~ main_02 연속 실행

# 단일 탭 내 특정 테스트 함수만 필터링 (-k 인자 전달)
.\run inspection user_info   # test_inspection_tab_user_info_matches_main 만 실행
.\run inspection start       # test_inspection_start_realtime_and_auto_navigation 만 실행
```

---

### 2-2. 53개 보안점검 항목 (`tests/security_checks`) — 번호별 실행

| 실행 명령 | 설명 | 예시 |
| :--- | :--- | :--- |
| `.\run <번호>` | 단일 보안점검 실행 | `.\run 7`, `.\run 14`, `.\run 45` |
| `.\run <시작>-<끝>` | 구간 연속 실행 | `.\run 2-14` |
| `.\run <번호,번호,...>` | 지정 번호 선택 실행 | `.\run 2,7,14` |
| `.\run pilot` | 시범 구현 점검(7, 14, 45번) 일괄 실행 | `.\run pilot` |
| `.\run tier_a` | Tier A 난이도 점검 전체 실행 | `.\run tier_a` |

---

### 2-3. 목록 확인 및 도움말
```powershell
.\run           # 전체 단축 실행 사용법 출력
.\run list      # pytest가 수집 가능한 전체 테스트 노드 목록 출력 (--collect-only -q)
```

---

## 3. `pytest` 직접 실행 치트시트

더 세밀한 제어나 리포트 생성이 필요할 때는 `.venv\Scripts\pytest.exe`를 직접 호출합니다.

```powershell
# 1. 마커 기반 실행 (-s: print 로그 실시간 출력, -v: 상세 결과)
.\.venv\Scripts\pytest.exe -m app_inspection -s -v

# 2. 복수 마커 조합 (and / or / not)
.\.venv\Scripts\pytest.exe -m "app_main and not main_04" -s
.\.venv\Scripts\pytest.exe -m "app_inspection or app_result" -s

# 3. 특정 파일 또는 특정 테스트 함수 직접 지정
.\.venv\Scripts\pytest.exe tests/app_checks/03_점검/test_inspection_progress.py -s
.\.venv\Scripts\pytest.exe tests/app_checks/03_점검/test_inspection_progress.py -k "user_info" -s

# 4. 실패한 테스트만 재실행 (--lf: last-failed) 또는 첫 실패 시 즉시 중단 (-x)
.\.venv\Scripts\pytest.exe -m app_check --lf -s
.\.venv\Scripts\pytest.exe -m app_main -x -s

# 5. HTML 테스트 리포트 생성 (pytest-html 활용)
.\.venv\Scripts\pytest.exe -m app_inspection --html=report_inspection.html --self-contained-html
```

---

## 4. 마커(Marker) 구조 요약 (`pytest.ini` 기준)

* **상위 그룹 마커**:
  * `app_check`: 프로그램 자체 UI/기능 점검 전체 (`tests/app_checks`)
  * `tier_a`, `tier_b`, `tier_c`: 53개 보안점검 난이도별 그룹
* **탭별 대분류 마커**:
  * `app_tray` (`tray_01` ~ `tray_07`)
  * `app_main` (`main_01` ~ `main_07`)
  * `app_inspection`
  * `app_history`
  * `app_clean`
  * `app_settings`
  * `app_result`
* **보안점검 개별 마커**:
  * `check01` ~ `check53`

