@echo off
cd /d "%~dp0"
py -3.12 -c "import sys,struct; assert sys.version_info[:2]==(3,12) and struct.calcsize('P')==8"
if errorlevel 1 goto fail
py -3.12 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install --no-index --find-links=vendor -r requirements.txt
if errorlevel 1 goto fail
echo Setup completed. Run start_windows.bat
pause
exit /b 0
:fail
echo Setup failed. Install Python 3.12 64-bit with Tcl/Tk and Python Launcher.
pause
exit /b 1
