@echo off
chcp 65001 > nul
echo ========================================
echo Ultimate M7 V2 - 라이브러리 설치
echo ========================================
echo.

echo 필수 라이브러리를 설치합니다...
echo.

pip install yfinance pandas vaderSentiment python-telegram-bot scipy plotly kaleido

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ 설치 중 오류 발생!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================
echo ✅ 모든 라이브러리 설치 완료!
echo ========================================
echo.
echo 이제 run_ultimate_v2.bat 을 실행하세요.
echo.
pause
