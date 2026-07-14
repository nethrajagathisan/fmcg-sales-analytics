@echo off
REM Enhanced batch file for FMCG Daily Sales Report
REM Logs execution, captures output, timestamps each run
REM Created for Windows Task Scheduler automation

setlocal enabledelayedexpansion

REM Set variables
set "ROOT_DIR=%~dp0"
set "PYTHON=C:\Program Files\Python311\python.exe"
set "SCRIPT=%ROOT_DIR%generate_daily_sales.py"
set "WORK_DIR=%ROOT_DIR%"
set "LOG_DIR=%ROOT_DIR%logs"
set "LOG_FILE=%LOG_DIR%\sales_generation.log"

REM Create logs directory if it doesn't exist
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Get current timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a:%%b)

REM Add to log file
(
echo.
echo ================================================================================
echo FMCG SALES GENERATION - %mydate% %mytime%
echo ================================================================================
echo Starting daily sales data generation...
echo.
) >> "%LOG_FILE%"

REM Run the Python script and capture output
cd /d "%WORK_DIR%"
"%PYTHON%" "%SCRIPT%" >> "%LOG_FILE%" 2>&1

REM Check if script succeeded
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Sales data generated successfully at %mydate% %mytime% >> "%LOG_FILE%"
    echo Task completed: PASS >> "%LOG_FILE%"
) else (
    echo [ERROR] Sales data generation FAILED (Error Code: %ERRORLEVEL%) >> "%LOG_FILE%"
    echo Task completed: FAIL >> "%LOG_FILE%"
)

echo. >> "%LOG_FILE%"

REM Log file location message (for troubleshooting)
echo Execution log saved to: %LOG_FILE%

endlocal
exit /b %ERRORLEVEL%
