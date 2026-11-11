param(
    [Parameter(Position=0)]
    $Target,
    [Parameter(Position=1)]
    $SubTarget
)

if ($Target -is [array]) { $Target = ($Target -join ",") } else { $Target = [string]$Target }
if ($SubTarget -is [array]) { $SubTarget = ($SubTarget -join ",") } else { $SubTarget = [string]$SubTarget }

$VenvPytest = Join-Path $PSScriptRoot ".venv\Scripts\pytest.exe"
$IsElevated = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not (Test-Path $VenvPytest)) {
    Write-Host "[오류] 가상환경 pytest를 찾을 수 없습니다: $VenvPytest" -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Target)) {
    Write-Host "[사용법]" -ForegroundColor Cyan
    Write-Host "  .\run <점검번호>     예: .\run 7, .\run 14, .\run 45"
    Write-Host "  .\run <시작-끝>      예: .\run 2-14 (2번부터 14번까지 연속 실행)"
    Write-Host "  .\run <번호,번호..>  예: .\run 2,7,14 (특정 번호들 골라서 연속 실행)"
    Write-Host "  .\run tray           트레이 아이콘 대분류 전체(Row 9~19) 실행"
    Write-Host "  .\run tray <번호>    트레이 아이콘 중분류별 실행 (1~6, 예: .\run tray 1, .\run tray 1-2, .\run tray list)"
    Write-Host "  .\run app            프로그램 자체 UI/기능 점검(app_checks) 전체 실행"
    Write-Host "  .\run pilot          구현된 시범 점검(7, 14, 45번) 일괄 실행"
    Write-Host "  .\run tier_a         Tier A 점검 실행"
    Write-Host "  .\run list           전체 점검 목록 확인"
    exit 0
}

if ($Target -eq "tray") {
    if (-not $IsElevated -and ($SubTarget -in "3", "4", "6" -or [string]::IsNullOrWhiteSpace($SubTarget) -or $SubTarget -match "[346]")) {
        Write-Host ">>> [참고] 트레이 우클릭 메뉴(3, 4, 6번)는 상위 보안 프로세스(taAssistant) 제어를 위해 '관리자 권한으로 실행한 PowerShell'이 권장됩니다." -ForegroundColor Yellow
    }
    if ([string]::IsNullOrWhiteSpace($SubTarget)) {
        Write-Host "[실행] 트레이 아이콘 대분류 전체(중분류 01~06, Row 9~19) 순차 실행 중..." -ForegroundColor Green
        & $VenvPytest -m app_tray -s
        exit $LASTEXITCODE
    }
    if ($SubTarget -eq "list") {
        Write-Host "[트레이 아이콘 중분류 목록 (Excel Row 9~19)]" -ForegroundColor Cyan
        Write-Host "  1 (tray_01) : 01_내PC보안점검         (Row 9~11  | TC 1_0001~1_0003)"
        Write-Host "  2 (tray_02) : 02_사용자정보입력       (Row 12~15 | TC 2_0001~2_0004)"
        Write-Host "  3 (tray_03) : 03_프로그램목록재확인   (Row 16    | TC 3_0001)"
        Write-Host "  4 (tray_04) : 04_폰트목록재확인       (Row 17    | TC 4_0001)"
        Write-Host "  5 (tray_05) : 05_에이전트업데이트실행 (Row 18    | TC 5_0001 [B/논의 요망])"
        Write-Host "  6 (tray_06) : 06_정보확인             (Row 19    | TC 6_0001)"
        exit 0
    }
    if ($SubTarget -match "^(\d+)[-~.]+(\d+)$") {
        $Start = [int]$Matches[1]
        $End = [int]$Matches[2]
        if ($Start -gt $End) { $Tmp = $Start; $Start = $End; $End = $Tmp }
        $Markers = ($Start..$End | ForEach-Object { "tray_{0:D2}" -f $_ }) -join " or "
        Write-Host "[실행] 트레이 중분류 $($Start)번~$($End)번 연속 실행 중..." -ForegroundColor Green
        & $VenvPytest -m $Markers -s
        exit $LASTEXITCODE
    }
    if ($SubTarget -match "^\d+(,\d+)+$") {
        $Nums = $SubTarget.Split(',') | ForEach-Object { [int]$_ }
        $Markers = ($Nums | ForEach-Object { "tray_{0:D2}" -f $_ }) -join " or "
        Write-Host "[실행] 트레이 중분류 지정($SubTarget) 실행 중..." -ForegroundColor Green
        & $VenvPytest -m $Markers -s
        exit $LASTEXITCODE
    }
    if ($SubTarget -match "^\d+$") {
        $Num = [int]$SubTarget
        $Marker = "tray_{0:D2}" -f $Num
        Write-Host "[실행] 트레이 중분류 $($Num)번($Marker) 실행 중..." -ForegroundColor Green
        & $VenvPytest -m $Marker -s
        exit $LASTEXITCODE
    }
    & $VenvPytest -m $SubTarget -s
    exit $LASTEXITCODE
}

if ($Target -match "^tray_?(\d+)$") {
    $Num = [int]$Matches[1]
    $Marker = "tray_{0:D2}" -f $Num
    Write-Host "[실행] 트레이 중분류 $($Num)번($Marker) 실행 중..." -ForegroundColor Green
    & $VenvPytest -m $Marker -s
    exit $LASTEXITCODE
}

if ($Target -eq "app") {
    Write-Host "[실행] 프로그램 자체 UI 및 기능 점검(app_checks) 실행 중..." -ForegroundColor Green
    & $VenvPytest -m app_check -s
    exit $LASTEXITCODE
}

if ($Target -eq "pilot") {
    Write-Host "[실행] 시범 구현 점검(7, 14, 45번) 실행 중..." -ForegroundColor Green
    & $VenvPytest -m "check07 or check14 or check45" -s
    exit $LASTEXITCODE
}

if ($Target -eq "list") {
    & $VenvPytest --collect-only -q
    exit $LASTEXITCODE
}

if ($Target -eq "tier_a") {
    Write-Host "[실행] Tier A 점검 실행 중..." -ForegroundColor Green
    & $VenvPytest -m tier_a -s
    exit $LASTEXITCODE
}

# 구간 지정 실행 (예: 2-14, 2..14, 2~14)
if ($Target -match "^(\d+)[-~.]+(\d+)$") {
    $Start = [int]$Matches[1]
    $End = [int]$Matches[2]
    if ($Start -gt $End) {
        $Tmp = $Start; $Start = $End; $End = $Tmp
    }
    $Markers = ($Start..$End | ForEach-Object { "check{0:D2}" -f $_ }) -join " or "
    Write-Host "[실행] $($Start)번부터 $($End)번 점검 연속 실행 중..." -ForegroundColor Green
    & $VenvPytest -m $Markers -s
    exit $LASTEXITCODE
}

# 콤마 구분 개별 지정 실행 (예: 2,7,14)
if ($Target -match "^\d+(,\d+)+$") {
    $Nums = $Target.Split(',') | ForEach-Object { [int]$_ }
    $Markers = ($Nums | ForEach-Object { "check{0:D2}" -f $_ }) -join " or "
    Write-Host "[실행] 지정 점검($Target) 연속 실행 중..." -ForegroundColor Green
    & $VenvPytest -m $Markers -s
    exit $LASTEXITCODE
}

if ($Target -match "^\d+$") {
    $Num = [int]$Target
    $Marker = "check{0:D2}" -f $Num
    Write-Host "[실행] $($Num)번 점검($Marker) 테스트 실행 중..." -ForegroundColor Green
    & $VenvPytest -m $Marker -s
    exit $LASTEXITCODE
}

& $VenvPytest -m $Target -s
exit $LASTEXITCODE
