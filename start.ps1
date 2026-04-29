# Second Brain - launch the optional FastAPI dashboard at http://localhost:8888

$ErrorActionPreference = "Stop"

# 1. Ensure venv exists
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

# 2. Activate venv
& ".venv\Scripts\Activate.ps1"

# 3. Install dependencies
Write-Host "Checking dependencies..."
pip install -r knowledge-base/requirements.txt --quiet

Write-Host "Starting Second Brain Dashboard..."
Write-Host "Open: http://localhost:8888"
Write-Host "-------------------------------------"
python knowledge-base/ui/app.py
