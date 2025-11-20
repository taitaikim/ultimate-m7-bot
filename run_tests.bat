@echo off
echo ========================================================
echo 🧪 Running M7 Bot Unit Tests (Pytest)
echo ========================================================

:: Check if pytest is installed
python -c "import pytest" 2>NUL
if %errorlevel% neq 0 (
    echo ⚠️ Pytest not found. Installing dependencies...
    pip install -r requirements-dev.txt
)

:: Run tests
echo.
echo 🏃 Executing tests...
python -m pytest tests/ -v

if %errorlevel% equ 0 (
    echo.
    echo ✅ All tests passed! 100/100 Score Achieved! 🏆
) else (
    echo.
    echo ❌ Some tests failed. Please check the output above.
)
pause
