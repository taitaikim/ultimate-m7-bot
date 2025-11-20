@echo off
chcp 65001 > nul
echo ========================================
echo Ultimate M7 V2 봇 - 작업 스케줄러 등록
echo ========================================
echo.

REM 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ 관리자 권한이 필요합니다!
    echo 이 파일을 마우스 우클릭 후 "관리자 권한으로 실행"을 선택하세요.
    pause
    exit /b 1
)

set SCRIPT_DIR=%~dp0
set BAT_FILE=%SCRIPT_DIR%run_ultimate_v2.bat

echo 스크립트 경로: %BAT_FILE%
echo.

REM 기존 작업 삭제 (있다면)
echo 기존 작업 스케줄러 삭제 중...
schtasks /Delete /TN "Ultimate_M7_Bot" /F >nul 2>&1
schtasks /Delete /TN "Ultimate_M7_V2_Bot" /F >nul 2>&1

echo.
echo 새로운 작업 스케줄러 등록 중...
echo 작업명: Ultimate_M7_V2_Bot
echo 실행 시간: 매일 오전 9시 (장 시작 전)
echo.

REM 작업 스케줄러 등록
schtasks /Create /SC DAILY /TN "Ultimate_M7_V2_Bot" /TR "%BAT_FILE%" /ST 09:00 /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ✅ 작업 스케줄러 등록 완료!
    echo ========================================
    echo.
    echo 📅 매일 오전 9시에 Ultimate M7 V2 봇이 자동 실행됩니다.
    echo.
    echo 확인 방법:
    echo 1. 작업 스케줄러 열기 (taskschd.msc)
    echo 2. "Ultimate_M7_V2_Bot" 작업 확인
    echo.
) else (
    echo.
    echo ❌ 작업 스케줄러 등록 실패!
    echo 오류 코드: %ERRORLEVEL%
    echo.
)

pause
