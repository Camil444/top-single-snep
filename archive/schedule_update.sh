#!/bin/bash
# Script de configuration pour planifier la mise à jour automatique
# Exécution : Chaque mardi à 18h00

# Configuration du cron job
CRON_SCHEDULE="0 18 * * 2"  # Mardi 18h00
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/update_data.py"
LOG_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/update_data.log"

echo "Configuration de la planification automatique..."
echo "Script: $SCRIPT_PATH"
echo "Schedule: Chaque mardi à 18h00"
echo "Logs: $LOG_PATH"

# Vérifier si le script existe
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Erreur: Script update_data.py non trouvé"
    exit 1
fi

# Ajouter au crontab
(crontab -l 2>/dev/null; echo "$CRON_SCHEDULE cd $(dirname $SCRIPT_PATH) && python3 $SCRIPT_PATH >> $LOG_PATH 2>&1") | crontab -

echo "✅ Planification configurée avec succès"
echo "Pour vérifier: crontab -l"
echo "Pour supprimer: crontab -e"

# Test manuel (optionnel)
echo ""
echo "Voulez-vous tester le script maintenant? (y/N)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "🚀 Test en cours..."
    cd "$(dirname "$SCRIPT_PATH")"
    python3 "$SCRIPT_PATH"
fi