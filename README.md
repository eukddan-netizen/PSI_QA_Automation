# topAegis 내PC보안점검 (TA-PSI) UI 자동화 프로젝트

`taKeeper.exe` (CefSharp 임베디드 웹뷰 기반 데스크톱 앱)의 **53개 보안점검**을 점검별 독립 폴더 구조로 테스트하는 Windows UI 자동화 프로젝트입니다.

## 폴더 구조

```text
psi_automation/
├─ core/                  # 앱 실행(트레이 더블클릭), 사용자 Default 데스크톱 전환
├─ pages/                 # 메인 페이지(점검 시작), 점검결과 페이지(행 탐색, 조치 클릭, 요약 점수/카운트 검증)
├─ common/                # 공통 OS 제어(레지스트리, 명령어), 백업/원복 가드(StateGuard), 5단계 표준 실행기
├─ tools/                 # UIA 요소 덤프 도구 (uia_dump.py)
├─ checks/
│  ├─ catalog.yaml        # 53개 점검 목록 (번호, 폴더명, UI 키워드, Tier 분류 및 근거, 구현 상태)
│  ├─ check_01_바이러스백신/
│  │  ├─ handler.py       # 이 점검 전용 OS 상태 주입 / 조회 / 원복
│  │  ├─ test_check_01.py # 점검 테스트
│  │  └─ README.md        # 점검 기준, 시나리오, 제외 사유(해당 시)
│  ├─ ... (총 53개 점검 폴더)
├─ conftest.py            # 공통 fixture (state_guard: 실패 시에도 OS 원래 값 자동 복구)
└─ pytest.ini             # importlib 모드 및 점검별(check01~check53)·Tier별 마커 등록
```

## 실행 방법

```powershell
# 특정 점검 1개만 실행 (예: 7번 화면보호기)
.\.venv\Scripts\pytest.exe -m check07 -s

# 시범 구현된 점검 실행 (7번 화면보호기, 14번 보안USB, 45번 절전모드)
.\.venv\Scripts\pytest.exe -m "check07 or check14 or check45" -s

# Tier A 점검 전체 실행 (구현 전 점검은 자동으로 skip 처리됨)
.\.venv\Scripts\pytest.exe -m tier_a

# 전체 53개 점검 수집 확인
.\.venv\Scripts\pytest.exe --collect-only
```
