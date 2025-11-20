@echo off
:: 현재 이 파일(run_m7.bat)이 있는 폴더로 위치를 강제 이동
cd /d "%~dp0"

:: 가상환경 안의 파이썬으로 봇 실행 (상위 폴더의 .venv 사용)
"..\.venv\Scripts\python.exe" m7_bot.py

:: 결과 확인을 위해 멈춤
pause