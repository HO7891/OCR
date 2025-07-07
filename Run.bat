@echo off
chcp 65001
cd /d C:\temp\AI
python Extract.py
python Import.py
timeout /t 5 >nul

#Extract.exe --input_folder myinput --output_folder myoutput
#Import.exe --mail_to someone@example.com
#pause
