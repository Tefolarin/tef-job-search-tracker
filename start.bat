@echo off
cd /d "%~dp0"
set PY=
rem Meaning matching needs Python 3.14 or older (its parts aren't built for 3.15 yet), so use one if installed
for %%V in (3.14 3.13 3.12) do (
  if not defined PY py -%%V -c "import sys" >nul 2>nul && set "PY=py -%%V"
)
if not defined PY where py >nul 2>nul && set PY=py
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY (
  echo Python is not installed, or "Add python.exe to PATH" was not ticked.
  echo Install it from python.org, tick that box, then double-click this file again.
  pause
  exit /b 1
)
echo Checking the helper packages (first run takes a minute)...
%PY% -m pip install --quiet --disable-pip-version-check flask openpyxl keyring pypdf python-docx
echo Checking meaning matching (first time only: a few minutes; if it fails, the tracker still works on keywords)...
%PY% -m pip install --quiet --disable-pip-version-check fastembed
echo.
%PY% app.py
echo.
echo The tracker has stopped. Press any key to close.
pause >nul
