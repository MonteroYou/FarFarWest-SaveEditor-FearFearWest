@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)

%PY% -c "import Crypto" >nul 2>nul
if errorlevel 1 (
    echo Installing required dependency: pycryptodome...
    %PY% -m pip install pycryptodome
    if errorlevel 1 (
        echo.
        echo Could not install pycryptodome. Make sure Python and pip are installed.
        pause
        exit /b 1
    )
)

%PY% save_editor_gui.py
if errorlevel 1 (
    echo.
    echo The editor exited with an error.
    pause
)
endlocal
