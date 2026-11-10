param(
    [Parameter(Position=0)]
    [string]$Target
)

$VenvPytest = Join-Path $PSScriptRoot ".venv\Scripts\pytest.exe"

if (-not (Test-Path $VenvPytest)) {
    Write-Host "[오류] 가상환경 pytest를 찾을 수 없습니다: $VenvPytest" -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Target)) {
    Write-Host "[사용법]" -ForegroundColor Cyan
    Write-Host "  .\run <점검번호>     예: .\run 7, .\run 14, .\run 45"
    Write-Host "  .\run <시작-끝>      예: .\run 2-14 (2번부터 14번까지 연속 실행)"
    Write-Host "  .\run <번호,번호..>  예: .\run 2,7,14 (특정 번호들 골라서 연속 실행)"
    Write-Host "  .\run pilot          구현된 시범 점검(7, 14, 45번) 일괄 실행"
    Write-Host "  .\run tier_a         Tier A 점검 실행"
    Write-Host "  .\run app            프로그램 자체 UI/기능 점검(app_checks) 실행"
    Write-Host "  .\run list           전체 점검 목록 확인"
    exit 0
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
