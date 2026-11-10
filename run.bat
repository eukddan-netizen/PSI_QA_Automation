@echo off
setlocal
chcp 65001 >nul

set VENV_PYTEST=%~dp0.venv\Scripts\pytest.exe

if not exist "%VENV_PYTEST%" (
    echo [오류] 가상환경 pytest를 찾을 수 없습니다: %VENV_PYTEST%
    exit /b 1
)

if "%~1"=="" (
    echo [사용법]
    echo   run ^<점검번호^>     예: run 7, run 14, run 45
    echo   run pilot          구현된 시범 점검^(7, 14, 45번^) 일괄 실행
    echo   run tier_a         Tier A 점검 실행
    echo   run app            프로그램 자체 UI/기능 점검^(app_checks^) 실행
    echo   run list           전체 점검 목록 확인
    exit /b 0
)

if /i "%~1"=="app" (
    echo [실행] 프로그램 자체 UI 및 기능 점검^(app_checks^) 실행 중...
    "%VENV_PYTEST%" -m app_check -s
    exit /b %errorlevel%
)

if /i "%~1"=="pilot" (
    echo [실행] 시범 구현 점검^(7, 14, 45번^) 실행 중...
    "%VENV_PYTEST%" -m "check07 or check14 or check45" -s
    exit /b %errorlevel%
)

if /i "%~1"=="list" (
    "%VENV_PYTEST%" --collect-only -q
    exit /b %errorlevel%
)

if /i "%~1"=="tier_a" (
    echo [실행] Tier A 점검 실행 중...
    "%VENV_PYTEST%" -m tier_a -s
    exit /b %errorlevel%
)

:: 숫자 입력 처리 (1자리 숫자를 2자리 check0N으로 변환)
set TARGET=%~1
set PADDED=0%TARGET%
set TWO_DIGIT=%PADDED:~-2%

echo [실행] %TWO_DIGIT%번 점검^(check%TWO_DIGIT%^) 테스트 실행 중...
"%VENV_PYTEST%" -m "check%TWO_DIGIT%" -s
exit /b %errorlevel%

