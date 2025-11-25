@echo off
REM =================================================
REM M7 Auto Scanner Launcher (Windows)
REM =================================================

echo ============================================
echo M7 Auto Scanner - Starting...
echo ============================================

REM 현재 스크립트 위치로 이동
cd /d "%~dp0"

REM Python 가상환경 확인 및 활성화
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment detected. Activating...
    call venv\Scripts\activate.bat
) else (
    echo [WARN] No virtual environment found. Using system Python.
)

REM scanner.py 실행
echo [INFO] Starting scanner.py...
echo ============================================
python scanner.py

REM 에러 확인
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================
    echo [ERROR] Scanner terminated with error code: %ERRORLEVEL%
    echo ============================================
) else (
    echo.
    echo ============================================
    echo [INFO] Scanner terminated normally.
    echo ============================================
)

REM 창이 바로 꺼지지 않도록 대기
pause