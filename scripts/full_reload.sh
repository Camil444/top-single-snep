#!/bin/bash
set -e

# Activer l'environnement virtuel si nécessaire
# source ../venv/bin/activate

echo "Réinitialisation de la base de données..."
python reset_db.py

echo "Démarrage du scraping complet..."

# Années passées (semaines 1 à 53)
for year in {2020..2024}
do
    echo "Traitement de l'année $year..."
    export TARGET_YEAR=$year
    export TARGET_WEEK=53
    python update.py
done

# Année en cours (jusqu'à la semaine 45 pour laisser 46 et 47 à Airflow)
echo "Traitement de l'année 2025 (jusqu'à semaine 45)..."
export TARGET_YEAR=2025
export TARGET_WEEK=45
python update.py

# Année en cours (jusqu'à la semaine actuelle)
echo "Traitement de l'année 2025..."
export TARGET_YEAR=2025
unset TARGET_WEEK
python update.py

echo "Chargement complet terminé !"
