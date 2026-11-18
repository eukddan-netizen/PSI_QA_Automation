param(
    [Parameter(Position = 0)]
    $Target,
    [Parameter(Position = 1)]
    $SubTarget,
    [switch]$Dashboard
)

if ($Target -is [array]) { $Target = ($Target -join ",") } else { $Target = [string]$Target }
if ($SubTarget -is [array]) { $SubTarget = ($SubTarget -join ",") } else { $SubTarget = [string]$SubTarget }
if ($Dashboard) { $env:PSI_DASHBOARD_RUN_ID = "cli_" + (Get-Date -Format "yyyyMMdd_HHmmss") }

$VenvPytest = Join-Path $PSScriptRoot ".venv\Scripts\pytest.exe"
$IsElevated = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not (Test-Path $VenvPytest)) {
    Write-Host "[오류] 가상환경 pytest를 찾을 수 없습니다: $VenvPytest" -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Target)) {
    Write-Host "[사용법]" -ForegroundColor Cyan
    Write-Host "  [보안점검 53개 항목]" -ForegroundColor Yellow
    Write-Host "    .\run <점검번호>     예: .\run 7, .\run 14, .\run 45"
    Write-Host "    .\run <시작-끝>      예: .\run 2-14 (2번부터 14번까지 연속 실행)"
    Write-Host "    .\run <번호,번호..>  예: .\run 2,7,14 (특정 번호들 골라서 연속 실행)"
    Write-Host "    .\run pilot          시범 구현 점검(7, 14, 45번) 일괄 실행"
    Write-Host "    .\run tier_a         Tier A 점검 전체 실행"
    Write-Host ""
    Write-Host "  [프로그램 UI/기능 점검 (탭별 대분류 - 한글/영문 모두 지원)]" -ForegroundColor Yellow
    Write-Host "    .\run app            app_checks 전체 실행 (.\run app list 로 탭 목록 확인)"
    Write-Host "    .\run 트레이 [번호]  (또는 tray)       트레이 아이콘 전체 또는 중분류(1~7, list)"
    Write-Host "    .\run 메인 [번호]    (또는 main)       메인 탭 전체 또는 중분류(1~7, list)"
    Write-Host "    .\run 점검           (또는 inspection) 점검 탭 실행"
    Write-Host "    .\run 점검결과       (또는 result)     점검결과 탭 공통 UI 실행"
    Write-Host "    .\run 점검이력       (또는 history)    점검이력 탭 실행"
    Write-Host "    .\run PC정리         (또는 clean)      PC정리 탭 실행"
    Write-Host "    .\run 설정           (또는 settings)   설정 탭 실행"
    Write-Host ""
    Write-Host "  [기타]" -ForegroundColor Yellow
    Write-Host "    .\run list           전체 pytest 테스트 목록 수집 확인"
    Write-Host "    .\run 대시보드       (또는 dashboard)  로컬 QA 대시보드 웹 서버 실행 (http://127.0.0.1:8000)"
    Write-Host "    .\run <대상> -Dashboard  대시보드로 실시간 로그 스트리밍하며 실행"
    exit 0
}

if ($Target -eq "dashboard" -or $Target -eq "대시보드" -or $Target -eq "dash") {
    & (Join-Path $PSScriptRoot "run_dashboard.ps1")
    exit $LASTEXITCODE
}

if ($Target -eq "tray" -or $Target -eq "트레이" -or $Target -eq "트레이아이콘") {
    if (-not $IsElevated -and ($SubTarget -in "2", "3", "4", "5", "7" -or [string]::IsNullOrWhiteSpace($SubTarget) -or $SubTarget -match "[23457]")) {
        Write-Host ">>> [참고] 트레이 우클릭 메뉴(2, 3, 4, 5, 7번)는 상위 보안 프로세스(taAssistant) 제어를 위해 '관리자 권한으로 실행한 PowerShell'이 권장됩니다." -ForegroundColor Yellow
    }
    if ([string]::IsNullOrWhiteSpace($SubTarget)) {
        Write-Host "[실행] 트레이 아이콘 대분류 전체(중분류 01~07) 순차 실행 중..." -ForegroundColor Green
        & $VenvPytest -m app_tray -s
        exit $LASTEXITCODE
    }
    if ($SubTarget -eq "list") {
        Write-Host "[트레이 아이콘 중분류 목록]" -ForegroundColor Cyan
        Write-Host "  1 (tray_01) : 01_내PC보안점검         (TC 1_0001~1_0003)"
        Write-Host "  2 (tray_02) : 02_패치현황             (TC 2_0001)"
        Write-Host "  3 (tray_03) : 03_사용자정보입력       (TC 3_0001~3_0004)"
        Write-Host "  4 (tray_04) : 04_프로그램목록재확인   (TC 4_0001)"
        Write-Host "  5 (tray_05) : 05_폰트목록재확인       (TC 5_0001)"
        Write-Host "  6 (tray_06) : 06_에이전트업데이트실행 (TC 6_0001 [B/논의 요망])"
        Write-Host "  7 (tray_07) : 07_정보확인             (TC 7_0001)"
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

if ($Target -eq "main" -or $Target -eq "메인" -or $Target -eq "메인화면") {
    if ([string]::IsNullOrWhiteSpace($SubTarget)) {
        Write-Host "[실행] 보안점검 메인 탭 대분류 전체(중분류 01~07) 순차 실행 중..." -ForegroundColor Green
        & $VenvPytest -m app_main -s
        exit $LASTEXITCODE
    }
    if ($SubTarget -eq "list") {
        Write-Host "[보안점검 메인 탭 중분류 목록]" -ForegroundColor Cyan
        Write-Host "  1 (main_01) : 01_점검정보       (Row 20~23: 방패 상태/종료경고/점검시작)"
        Write-Host "  2 (main_02) : 02_PC보안지표     (Row 24: 보안지표 hover 툴팁)"
        Write-Host "  3 (main_03) : 03_사용자정보     (Row 25~26: 최근점검일시/갱신)"
        Write-Host "  4 (main_04) : 04_도움말         (Row 27~31: 소개모달/nav_bar/언어/아코디언)"
        Write-Host "  5 (main_05) : 05_암호안전성검사 (Row 32: 암호 안전성 검사 모달)"
        Write-Host "  6 (main_06) : 06_지난검사내역   (Row 33~34: hover 점수/이력 상세 이동)"
        Write-Host "  7 (main_07) : 07_지원및문의     (Row 35: 환경설정 문의처 변경 및 앱 하단 문구 연동/원복)"
        exit 0
    }
    if ($SubTarget -match "^(\d+)[-~.]+(\d+)$") {
        $Start = [int]$Matches[1]
        $End = [int]$Matches[2]
        if ($Start -gt $End) { $Tmp = $Start; $Start = $End; $End = $Tmp }
        $Markers = ($Start..$End | ForEach-Object { "main_{0:D2}" -f $_ }) -join " or "
        Write-Host "[실행] 보안점검 메인 탭 중분류 $($Start)번~$($End)번 연속 실행 중..." -ForegroundColor Green
        & $VenvPytest -m $Markers -s
        exit $LASTEXITCODE
    }
    if ($SubTarget -match "^\d+(,\d+)+$") {
        $Nums = $SubTarget.Split(',') | ForEach-Object { [int]$_ }
        $Markers = ($Nums | ForEach-Object { "main_{0:D2}" -f $_ }) -join " or "
        Write-Host "[실행] 보안점검 메인 탭 중분류 지정($SubTarget) 실행 중..." -ForegroundColor Green
        & $VenvPytest -m $Markers -s
        exit $LASTEXITCODE
    }
    if ($SubTarget -match "^\d+$") {
        $Num = [int]$SubTarget
        $Marker = "main_{0:D2}" -f $Num
        Write-Host "[실행] 보안점검 메인 탭 중분류 $($Num)번($Marker) 실행 중..." -ForegroundColor Green
        & $VenvPytest -m $Marker -s
        exit $LASTEXITCODE
    }
    & $VenvPytest -m $SubTarget -s
    exit $LASTEXITCODE
}

if ($Target -match "^main_?(\d+)$") {
    $Num = [int]$Matches[1]
    $Marker = "main_{0:D2}" -f $Num
    Write-Host "[실행] 보안점검 메인 탭 중분류 $($Num)번($Marker) 실행 중..." -ForegroundColor Green
    & $VenvPytest -m $Marker -s
    exit $LASTEXITCODE
}

if ($Target -eq "app") {
    if ($SubTarget -eq "list") {
        Write-Host "[프로그램 UI/기능 점검(app_checks) 대분류 목록]" -ForegroundColor Cyan
        Write-Host "  tray        (app_tray)       : 01_트레이                 (트레이 아이콘, 중분류 1~7)"
        Write-Host "  main        (app_main)       : 02_메인                   (메인 탭, 중분류 1~7)"
        Write-Host "  inspection  (app_inspection) : 03_점검                   (점검 탭)"
        Write-Host "  result      (app_result)     : 04_점검결과               (점검결과 탭)"
        Write-Host "  history     (app_history)    : 05_점검이력               (점검이력 탭)"
        Write-Host "  clean       (app_clean)      : 06_PC정리                 (PC정리 탭)"
        Write-Host "  settings    (app_settings)   : 07_설정                   (설정 탭)"
        exit 0
    }
    Write-Host "[실행] 프로그램 자체 UI 및 기능 점검(app_checks) 실행 중..." -ForegroundColor Green
    & $VenvPytest -m app_check -s
    exit $LASTEXITCODE
}

$TabMarkerMap = @{
    "점검"         = @{ Marker = "app_inspection"; Label = "점검 탭 (03_점검)" }
    "inspection" = @{ Marker = "app_inspection"; Label = "점검 탭 (03_점검)" }
    "insp"       = @{ Marker = "app_inspection"; Label = "점검 탭 (03_점검)" }
    "점검결과"       = @{ Marker = "app_result"; Label = "점검결과 탭 (04_점검결과)" }
    "result"     = @{ Marker = "app_result"; Label = "점검결과 탭 (04_점검결과)" }
    "점검이력"       = @{ Marker = "app_history"; Label = "점검이력 탭 (05_점검이력)" }
    "history"    = @{ Marker = "app_history"; Label = "점검이력 탭 (05_점검이력)" }
    "PC정리"       = @{ Marker = "app_clean"; Label = "PC정리 탭 (06_PC정리)" }
    "clean"      = @{ Marker = "app_clean"; Label = "PC정리 탭 (06_PC정리)" }
    "설정"         = @{ Marker = "app_settings"; Label = "설정 탭 (07_설정)" }
    "settings"   = @{ Marker = "app_settings"; Label = "설정 탭 (07_설정)" }
}

if ($TabMarkerMap.ContainsKey($Target)) {
    $Info = $TabMarkerMap[$Target]
    Write-Host "[실행] $($Info.Label) 테스트 실행 중..." -ForegroundColor Green
    if ([string]::IsNullOrWhiteSpace($SubTarget)) {
        & $VenvPytest -m $Info.Marker -s
    }
    else {
        & $VenvPytest -m $Info.Marker -k $SubTarget -s
    }
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
