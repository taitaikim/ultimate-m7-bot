@echo off
REM ========================================
REM M7 Bot 주간 리포트 생성
REM ========================================

echo ======================================
echo    M7 Bot 주간 리포트 생성
echo ======================================
echo.

cd /d "%~dp0"

REM 주간 리포트 생성
python weekly_summary.py

REM HTML 리포트 열기
if exist performance_summary.html (
    echo.
    echo 리포트를 브라우저에서 여는 중...
    start performance_summary.html
)

echo.
echo ======================================
echo    완료!
echo ======================================
echo.

pause
exit
