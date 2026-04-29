# Second Brain - note ingestion pipeline (PowerShell wrapper).
#
# Usage:
#   .\brain.ps1 <path_to_note>
#
# Creates a venv on first run, installs dependencies, normalizes the note via
# Claude, then rebuilds the knowledge index.

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$NotePath
)

$ErrorActionPreference = "Stop"

# 1. Ensure venv exists
if (-not (Test-Path ".venv")) {
    Write-Host "Initializing virtual environment..."
    python -m venv .venv
}

# 2. Activate venv
& ".venv\Scripts\Activate.ps1"

# 3. Ensure core dependencies
pip install python-frontmatter --quiet

# 4. Normalize and ingest
Write-Host "Processing note: $NotePath"
python knowledge-base/scripts/normalize_notes.py $NotePath

# 5. Rebuild index
Write-Host "Rebuilding index..."
python knowledge-base/scripts/build_index.py
