@echo off
chcp 65001
cls

echo ==========================================
echo 🤖 M7 봇 자동 실행 스케줄러 설정
echo ==========================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ 이 스크립트는 관리자 권한이 필요합니다.
    echo 마우스 우클릭 후 "관리자 권한으로 실행"을 선택해주세요.
    echo.
    pause
    exit /b 1
)

:: 현재 스크립트 경로 기준으로 run_ultimate.bat 절대 경로 설정
set SCRIPT_DIR=%~dp0
set BAT_PATH=%SCRIPT_DIR%run_ultimate.bat

echo 📂 실행 파일 경로: %BAT_PATH%
echo.

:: 기존 작업이 있다면 삭제
schtasks /Query /TN "M7_Auto_Bot" >nul 2>&1
if %errorLevel% equ 0 (
    echo ⚠️  기존 작업 발견. 삭제 중...
    schtasks /Delete /TN "M7_Auto_Bot" /F
)

:: 새 작업 등록
echo 📝 작업 스케줄러에 등록 중...
schtasks /Create ^
    /TN "M7_Auto_Bot" ^
    /TR "\"%BAT_PATH%\"" ^
    /SC DAILY ^
    /ST 23:30 ^
    /RL HIGHEST ^
    /F

if %errorLevel% equ 0 (
    echo.
    echo ==========================================
    echo ✅ 등록 완료!
    echo ==========================================
    echo.
    echo 📌 작업 이름: M7_Auto_Bot
    echo ⏰ 실행 시간: 매일 밤 11시 30분
    echo 📂 실행 파일: %BAT_PATH%
    echo 🔑 권한: 최고 권한으로 실행
    echo.
    echo 💡 작업 스케줄러에서 확인하려면:
    echo    1. Win + R 키를 누르고
    echo    2. "taskschd.msc" 입력 후 엔터
    echo    3. "M7_Auto_Bot" 작업을 찾으세요
    echo.
) else (
    echo.
    echo ❌ 등록 실패. 오류가 발생했습니다.
    echo.
)

pause
