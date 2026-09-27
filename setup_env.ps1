Write-Host "Creating Python Virtual Environment (venv)..." -ForegroundColor Cyan
python -m venv venv

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create virtual environment. Ensure Python is installed." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
.\venv\Scripts\Activate.ps1

Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host "Environment setup complete!" -ForegroundColor Green
