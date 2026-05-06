# ORCID Explorer - Lancement rapide
# Usage : .\lancer.ps1

$currentPolicy = Get-ExecutionPolicy -Scope CurrentUser
if ($currentPolicy -eq "Restricted" -or $currentPolicy -eq "Undefined") {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
}

Write-Host ""
Write-Host "ORCID Explorer - http://localhost:5000"
Write-Host "Ctrl+C pour arreter"
Write-Host ""

& ".venv\Scripts\python.exe" app.py
