param(
    [int]$Port = 8000,
    [switch]$NoBrowser
)

$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "[오류] 가상환경 Python을 찾을 수 없습니다: $VenvPython" -ForegroundColor Red
    exit 1
}

# Check if port is already in use
$Listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($Listeners) {
    $Pids = $Listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($OldPid in $Pids) {
        $ProcInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$OldPid" -ErrorAction SilentlyContinue
        $CmdLine = if ($ProcInfo) { [string]$ProcInfo.CommandLine } else { "" }
        if ($CmdLine -match "dashboard\.main") {
            Write-Host "[QA Dashboard] 기존 대시보드 서버(PID $OldPid)를 종료하고 새로 시작합니다..." -ForegroundColor Yellow
            try {
                Stop-Process -Id $OldPid -Force -ErrorAction Stop
                Start-Sleep -Milliseconds 500
            }
            catch {
                Write-Host "[오류] 기존 서버(PID $OldPid) 종료 실패 (관리자 권한으로 실행 중일 수 있음): $_" -ForegroundColor Red
                Write-Host "       관리자 PowerShell에서 실행하거나 다른 포트를 사용하세요: .\run_dashboard.ps1 -Port 8001" -ForegroundColor Yellow
                exit 1
            }
        }
        else {
            $ProcName = if ($ProcInfo) { $ProcInfo.Name } else { "Unknown" }
            Write-Host "[오류] 포트 $Port 가 이미 다른 프로세스($ProcName, PID $OldPid)에 의해 사용 중입니다." -ForegroundColor Red
            Write-Host "       다른 포트로 실행하려면: .\run_dashboard.ps1 -Port 8001" -ForegroundColor Yellow
            exit 1
        }
    }
}

$Url = "http://127.0.0.1:$Port"
Write-Host "[QA Dashboard] 로컬 대시보드 서버 시작: $Url" -ForegroundColor Cyan
Write-Host "[QA Dashboard] 종료하려면 Ctrl+C를 누르세요." -ForegroundColor DarkGray

if (-not $NoBrowser) {
    Start-Job -ScriptBlock {
        param($TargetUrl)
        Start-Sleep -Seconds 1
        Start-Process $TargetUrl
    } -ArgumentList $Url | Out-Null
}

& $VenvPython -m dashboard.main --host 127.0.0.1 --port $Port
