@echo off
:: 프로젝트 폴더로 정확하게 이동
cd /d "C:\Users\user\Desktop\Developement\stock-crawler"

:: 가상환경 켜기
call .venv\Scripts\activate

:: 봇 실행
python rsi_bot.py

:: 창 꺼짐 방지
pause