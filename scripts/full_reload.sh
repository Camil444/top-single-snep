#!/bin/bash
set -e

# Activate virtual environment if necessary
# source ../venv/bin/activate

echo "Réinitialisation de la base de données..."
python reset_db.py

echo "Démarrage du scraping complet..."

# Past years (weeks 1 to 53)
for year in {2020..2024}
do
    echo "Traitement de l'année $year..."
    export TARGET_YEAR=$year
    export TARGET_WEEK=53
    python update.py
done

# Current year (up to week 45 to leave 46 and 47 for Airflow)
echo "Traitement de l'année 2025 (jusqu'à semaine 45)..."
export TARGET_YEAR=2025
export TARGET_WEEK=45
python update.py

# Current year (up to current week)
echo "Traitement de l'année 2025..."
export TARGET_YEAR=2025
unset TARGET_WEEK
python update.py

echo "Chargement complet terminé !"
