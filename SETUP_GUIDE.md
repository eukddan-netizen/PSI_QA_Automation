# TA-PSI UI 자동화 & QA 대시보드 환경 구축 가이드 (새 PC 세팅용)

이 문서는 새로운 Windows PC에 **PSI_QA_Automation** 테스트 환경과 **로컬 QA 웹 대시보드**를 처음부터 구축하고, 실행하기까지의 전체 절차를 순서대로 정리한 가이드입니다.

---

## 0. 사전 확인 사항 (새 PC 조건)

테스트를 돌리기 전에 새 PC가 아래 조건을 만족하는지 확인해 주세요.

| 항목 | 확인 내용 |
|---|---|
| **OS** | Windows 10 / 11 (한국어판 권장) |
| **테스트 대상 앱** | `내PC보안점검 (taKeeper.exe)` 설치 완료 및 **시스템 트레이에 아이콘 실행 중** |
| **네트워크** | 관리 서버(`https://192.168.4.151`)에 접속 가능 |
| **단말 등록** | 현재 PC가 관리 서버에 사용자로 등록되어 있음 (IP 기반 검색용) |
| **웹 브라우저** | Google Chrome 설치 완료 (관리자 웹 연동 및 대시보드 접속용) |
| **계정 권한** | Windows 관리자 권한 (일부 점검 및 트레이 우클릭 메뉴 테스트 시 필수) |

---

## 1. 필수 프로그램 설치

### ① Git 설치
PowerShell을 열어 아래 명령어로 설치 여부를 확인합니다.
```powershell
git --version
```
설치되어 있지 않다면 [Git for Windows](https://git-scm.com/download/win)에서 다운로드 후 기본 옵션으로 설치합니다.

### ② Python 3.12 (64-bit) 설치
```powershell
python --version
```
설치되어 있지 않다면 [Python 공식 다운로드](https://www.python.org/downloads/windows/)에서 **Python 3.12 (64-bit)** 를 받아 설치합니다.

> ⚠️ **주의 (설치 시 필수 체크 사항)**
> 1. 설치 첫 화면 하단의 **`Add python.exe to PATH`** 를 **반드시 체크**하세요.
> 2. 반드시 **64-bit** 버전을 설치하세요. (`pywinauto` 동작 시 비트 일치 필요)

### ③ Node.js (LTS) 설치 — QA 웹 대시보드 빌드용
로컬 QA 웹 대시보드 프론트엔드(`frontend/`)를 빌드하기 위해 Node.js(LTS, v20 이상 권장)가 필요합니다.
```powershell
node --version
npm --version
```
설치되어 있지 않다면 [Node.js 공식 사이트](https://nodejs.org/)에서 **LTS 버전**을 받아 기본 옵션으로 설치한 뒤 PowerShell을 재시작합니다.

### ④ (선택) Antigravity IDE 설치
IDE에서 AI와 함께 테스트 실행·수정을 진행할 경우 Antigravity IDE를 설치하고 로그인합니다.
> 💡 시스템 레지스트리 및 보안 프로세스 제어를 위해 **관리자 권한으로 실행**하는 것을 권장합니다.

---

## 2. 프로젝트 내려받기 (`git clone`)

PowerShell을 열고 원하는 위치(예: `D:\` 또는 `C:\`)로 이동한 뒤 저장소를 클론합니다.

```powershell
cd D:\
git clone https://github.com/eukddan-netizen/PSI_QA_Automation.git psi_automation
cd D:\psi_automation
```
> 비공개 저장소인 경우 GitHub 로그인 창이 뜨면 권한이 있는 계정으로 로그인해 주세요.

---

## 3. Python 가상환경(`.venv`) 및 패키지 설치

프로젝트 루트 폴더(`D:\psi_automation`) 안에서 아래 명령어를 **순서대로** 실행합니다.

```powershell
# 1) 가상환경 생성 (폴더 이름은 반드시 .venv 여야 합니다)
python -m venv .venv

# 2) pip 최신화
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# 3) 필수 패키지 일괄 설치 (pytest, pywinauto, playwright, fastapi, openpyxl, python-docx 등)
.\.venv\Scripts\pip.exe install -r requirements.txt
```

> 참고: `run.ps1`과 `run_dashboard.ps1` 스크립트는 `.venv\Scripts\python.exe` / `pytest.exe` 경로를 사용하므로 가상환경 폴더 이름은 꼭 `.venv` 로 만들어야 합니다.

---

## 4. QA 웹 대시보드 프론트엔드 빌드 (최초 1회)

프론트엔드 빌드 산출물(`dashboard/static/`)과 `frontend/node_modules/`는 `.gitignore`에 의해 Git 저장소에 포함되지 않습니다. 따라서 새 PC에서 클론한 직후 아래 명령어로 프론트엔드를 한 번 빌드해야 대시보드 웹 화면이 정상 표시됩니다.

```powershell
cd D:\psi_automation\frontend
npm install
npm run build
cd D:\psi_automation
```
정상 완료 시 `../dashboard/static/index.html` 및 에셋 파일이 생성됩니다.

---

## 5. PowerShell 실행 권한 설정 (최초 1회)

PowerShell에서 `.\run` 명령 실행 시 *"이 시스템에서 스크립트를 실행할 수 없으므로..."* 오류가 발생하면 아래 명령어를 한 번만 입력해 주세요.

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
*(또는 `.\run.bat list` 처럼 `.bat` 파일을 직접 실행하면 위 설정 없이도 동작합니다.)*

---

## 6. 정상 설치 및 화면 인식 확인

### ① 테스트 목록 수집 확인
```powershell
.\run list
```
전체 테스트 목록이 오류 없이 출력되면 파이썬과 pytest 세팅은 완료된 것입니다.

### ② 데스크톱 화면 인식(UIA) 확인
`내PC보안점검` 창을 화면에 띄워 둔 상태에서 아래 명령어를 실행합니다.
```powershell
.\.venv\Scripts\python.exe tools\uia_dump.py
```
`Total elements: ...` 와 함께 화면 요소 목록이 출력되고 `reports/window_elements.txt` 파일이 생성되면 정상입니다.

---

## 7. 테스트 및 QA 웹 대시보드 실행

### ① 로컬 QA 웹 대시보드 실행 (권장)
1. 시작 메뉴에서 **PowerShell**을 마우스 우클릭 → **관리자 권한으로 실행**으로 엽니다.
2. 프로젝트 폴더로 이동해 대시보드 서버를 시작합니다.

```powershell
cd D:\psi_automation
.\run.ps1 dashboard
```
- 자동으로 `http://127.0.0.1:8000` 웹 대시보드가 열립니다.
- 상단에서 테스트 프리셋(`app_checks 전체`, `01_트레이` 등)을 선택해 **`테스트 실행`** 버튼을 누르면 실시간 로그 스트리밍 및 자동 포커스 트리가 동작합니다.
- 실행 중 또는 완료 후 우측 상단 **`Excel`** / **`Word`** 버튼으로 해당 시점까지의 완료 데이터를 대한민국 정부 보고서 양식(`.xlsx`, `.docx`)으로 즉시 다운로드할 수 있습니다.

### ② CLI 실행과 대시보드 실시간 연동 (병행 사용)
대시보드를 띄워 둔 상태에서 별도의 관리자 PowerShell 창으로 기존 CLI 명령에 `-Dashboard` 옵션만 붙여 실행해도 동일한 대시보드 화면으로 로그가 실시간 스트리밍됩니다.
```powershell
.\run.ps1 app -Dashboard
.\run.ps1 tray 1 -Dashboard
.\.venv\Scripts\pytest.exe -m app_result --dashboard -s
```

### ③ CLI 단독 테스트 실행
```powershell
# 가장 기본적인 7번(화면보호기) 점검 테스트 실행
.\run 7

# 시범 점검(7, 14, 45번) 일괄 실행
.\run pilot

# 관리자 웹 연동까지 확인 (메인 탭 > 사용자 정보)
.\run main 3
```

---

## 8. 코드 최신화 방법 (`git pull`)

원격 저장소에 코드가 업데이트되었을 때, 아래 명령어로 최신 상태를 내려받습니다.

```powershell
cd D:\psi_automation
git pull

# 1) requirements.txt가 변경되었다면 실행
.\.venv\Scripts\pip.exe install -r requirements.txt

# 2) frontend/ 소스가 변경되었다면 대시보드 UI 재빌드
cd frontend
npm install
npm run build
cd ..
```

---

## 9. 자주 발생하는 문제 해결 (트러블슈팅)

1. **`http://127.0.0.1:8000` 접속 시 `{"detail":"Not Found"}` 또는 빈 화면이 뜨는 경우**
   - `frontend` 빌드가 아직 실행되지 않아 `dashboard/static/index.html`이 없는 상태입니다. **4장(프론트엔드 빌드)**의 `npm install && npm run build`를 실행한 뒤 대시보드를 재시작하세요.
2. **`WinError 10048` 포트 충돌이 발생하는 경우**
   - `.\run.ps1 dashboard`는 기존 `dashboard.main` 프로세스를 자동 종료 후 재시작합니다. 만약 관리자 권한으로 실행된 이전 서버나 다른 앱이 8000번 포트를 점유 중이라면 관리자 PowerShell에서 실행하거나 다른 포트로 띄우세요.
   ```powershell
   .\run_dashboard.ps1 -Port 8001
   ```
3. **`.\run` 실행 시 한글 파싱 오류가 나는 경우**
   - `git pull`을 받아 최신 `run.ps1` (UTF-8 BOM 적용 버전)으로 업데이트하거나, `.\run.bat list`를 사용하세요.
4. **트레이 메뉴나 레지스트리 테스트가 실패/스킵되는 경우**
   - 대시보드 또는 테스트를 실행하는 PowerShell / IDE가 **관리자 권한**으로 실행되었는지 확인하세요. (대시보드 좌측 상단에 `관리자 권한` 배지로 확인 가능)
5. **테스트 도중 창을 못 찾거나 클릭이 빗나가는 경우**
   - 테스트 실행 중에는 PC 화면이 잠기지 않아야 합니다.
   - 원격 데스크톱(RDP)으로 접속해 실행할 경우, 창을 최소화하거나 연결을 끊으면 GUI가 사라져 실패합니다.
   - 화면 배율(DPI)이 너무 크거나 다르면 일부 고정 좌표 기반 동작에 영향이 있을 수 있습니다.
6. **더 자세한 테스트 실행 명령어가 궁금할 때**
   - [TEST_RUN_GUIDE.md](TEST_RUN_GUIDE.md) 문서를 참고하세요.
