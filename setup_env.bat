@echo off
echo Creating Python Virtual Environment (venv)...
python -m venv venv

if %ERRORLEVEL% NEQ 0 (
    echo Python was not found or failed to create venv. Please ensure Python is installed and in your PATH.
    pause
    exit /b %ERRORLEVEL%
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo Environment setup complete!
pause
