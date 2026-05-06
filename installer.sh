#!/bin/bash
# ORCID Explorer - Script d'installation (macOS / Linux)
# Usage : chmod +x installer.sh && ./installer.sh

set -e  # Arreter si une commande echoue

echo ""
echo "================================================"
echo "   ORCID Explorer - Installation"
echo "================================================"
echo ""

# ── 1. Verifier Python ────────────────────────────────────────
echo "[1/5] Verification de Python..."

# Chercher python3 ou python
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "      ERREUR : Python introuvable."
    echo "      Installez Python 3.10+ depuis https://python.org"
    echo "      Sur Mac, vous pouvez aussi utiliser Homebrew : brew install python"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "      OK : $PYTHON_VERSION"

# ── 2. Creer l'environnement virtuel ─────────────────────────
echo ""
echo "[2/5] Creation de l'environnement virtuel (.venv)..."

if [ -d ".venv" ]; then
    echo "      Environnement existant detecte - suppression..."
    rm -rf .venv
fi

$PYTHON_CMD -m venv .venv
echo "      OK : Environnement virtuel cree"

# ── 3. Verifier l'environnement ───────────────────────────────
echo ""
echo "[3/5] Verification de l'environnement virtuel..."
echo "      OK"

# ── 4. Installer les dependances ──────────────────────────────
echo ""
echo "[4/5] Installation des dependances (Flask, requests)..."

.venv/bin/pip install -r requirements.txt --quiet
echo "      OK : Dependances installees"

# ── 5. Lancer l'application ───────────────────────────────────
echo ""
echo "[5/5] Demarrage de l'application..."
echo ""
echo "================================================"
echo "   Ouvrez votre navigateur : http://localhost:5000"
echo "   Pour arreter : Ctrl+C"
echo "================================================"
echo ""

.venv/bin/python app.py
