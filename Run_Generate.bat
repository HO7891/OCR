@echo off
setlocal

REM 內部參數：1=最小化，0=正常顯示
set MINIMIZE=0

chcp 65001
cd /d C:\temp\AI

if "%MINIMIZE%"=="1" (
    start /min python Genrate.py
) else (
    python Genrate.py
)

timeout /t 5 >nul

#Extract.exe --input_folder myinput --output_folder myoutput
#Import.exe --mail_to someone@example.com
#pause
