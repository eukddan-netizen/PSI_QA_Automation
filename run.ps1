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
    Write-Host "  .\run pilot          구현된 시범 점검(7, 14, 45번) 일괄 실행"
    Write-Host "  .\run tier_a         Tier A 점검 실행"
    Write-Host "  .\run list           전체 53개 점검 목록 확인"
    exit 0
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

if ($Target -match "^\d+$") {
    $Num = [int]$Target
    $Marker = "check{0:D2}" -f $Num
    Write-Host "[실행] $Num번 점검($Marker) 테스트 실행 중..." -ForegroundColor Green
    & $VenvPytest -m $Marker -s
    exit $LASTEXITCODE
}

& $VenvPytest -m $Target -s
exit $LASTEXITCODE
