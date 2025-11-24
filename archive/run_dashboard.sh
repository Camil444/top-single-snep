#!/bin/bash
# Script de lancement du dashboard des producteurs musicaux

echo "🎵 Lancement du Dashboard des Producteurs Musicaux"
echo "=================================================="

# Vérifier que les dépendances sont installées
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit non installé. Installation..."
    pip install -r requirements.txt
fi

# Lancement du dashboard
echo "🚀 Démarrage du dashboard..."
echo "📍 URL: http://localhost:8501"
echo "⏹️  Arrêt: Ctrl+C"
echo ""

streamlit run frontend_dashboard.py