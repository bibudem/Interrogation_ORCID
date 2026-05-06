#!/bin/bash
# ORCID Explorer - Lancement rapide (macOS / Linux)
# Usage : ./lancer.sh

if [ ! -d ".venv" ]; then
    echo "ERREUR : Environnement virtuel introuvable."
    echo "Lancez d'abord : ./installer.sh"
    exit 1
fi

echo ""
echo "ORCID Explorer - http://localhost:5000"
echo "Ctrl+C pour arreter"
echo ""

.venv/bin/python app.py
