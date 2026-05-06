# ORCID Explorer - Script d installation
# Usage : .\installer.ps1

Write-Host ""
Write-Host "================================================"
Write-Host "   ORCID Explorer - Installation"
Write-Host "================================================"
Write-Host ""

# 1. Verifier Python
Write-Host "[1/5] Verification de Python..."

try {
    $pythonVersion = python --version 2>&1
    Write-Host "      OK : $pythonVersion"
} catch {
    Write-Host "      ERREUR : Python introuvable."
    Write-Host "      Installez Python 3.10+ depuis https://python.org"
    Write-Host "      Cochez bien Add Python to PATH lors de l installation."
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

# 2. Creer l environnement virtuel
Write-Host ""
Write-Host "[2/5] Creation de l environnement virtuel (.venv)..."

if (Test-Path ".venv") {
    Write-Host "      Environnement existant detecte - suppression..."
    Remove-Item -Recurse -Force ".venv"
}

python -m venv .venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "      ERREUR : Echec de la creation du venv."
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}
Write-Host "      OK : Environnement virtuel cree"

# 3. Ajuster la politique d execution si necessaire
Write-Host ""
Write-Host "[3/5] Verification de la politique d execution PowerShell..."

$currentPolicy = Get-ExecutionPolicy -Scope CurrentUser
if ($currentPolicy -eq "Restricted" -or $currentPolicy -eq "Undefined") {
    Write-Host "      Ajustement en cours..."
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
}
Write-Host "      OK"

# 4. Installer les dependances
Write-Host ""
Write-Host "[4/5] Installation des dependances (Flask, requests)..."

& ".venv\Scripts\pip.exe" install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "      ERREUR : Echec de l installation des dependances."
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}
Write-Host "      OK : Dependances installees"

# 5. Lancer l application
Write-Host ""
Write-Host "[5/5] Demarrage de l application..."
Write-Host ""
Write-Host "================================================"
Write-Host "   Ouvrez votre navigateur : http://localhost:5000"
Write-Host "   Pour arreter : Ctrl+C"
Write-Host "================================================"
Write-Host ""

& ".venv\Scripts\python.exe" app.py
