@echo off
setlocal
title Number Matching Memory Game

REM Move to the folder containing this .bat file.
cd /d "%~dp0"

echo ==========================================
echo   Number Matching Memory Game
echo ==========================================
echo.

REM Check that Python 3.13 is installed.
py -3.13 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.13 was not found.
    echo Install Python 3.13, then try again.
    echo Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [1/3] Checking pip...
py -3.13 -m pip --version
if errorlevel 1 (
    echo ERROR: pip is not available for Python 3.13.
    pause
    exit /b 1
)

echo.
echo [2/3] Installing project requirements...
if exist "requirements.txt" (
    py -3.13 -m pip install -r requirements.txt
) else (
    py -3.13 -m pip install pygame==2.6.1
)
if errorlevel 1 (
    echo.
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

if not exist "main.py" (
    echo.
    echo ERROR: main.py was not found.
    echo Put this BAT file in the same folder as main.py.
    pause
    exit /b 1
)

echo.
echo [3/3] Starting the game...
py -3.13 main.py

if errorlevel 1 (
    echo.
    echo The game closed with an error. Read the message above.
    pause
)

endlocal
