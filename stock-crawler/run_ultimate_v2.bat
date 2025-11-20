@echo off
chcp 65001 > nul
echo ========================================
echo Ultimate M7 V2 Bot (고급 기술적 분석)
echo ========================================
echo.

cd /d "%~dp0"
python ultimate_v2.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ 오류 발생! 에러 코드: %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ✅ 실행 완료!
pause
