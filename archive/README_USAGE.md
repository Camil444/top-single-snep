# 🎵 Système de Mise à Jour Automatique - Données Musicales

## 📋 Fichiers créés

### Scripts principaux
- `update_data.py` - Script de mise à jour automatique avec API Genius
- `producer_analytics.py` - Analyseur de données pour les producteurs
- `frontend_dashboard.py` - Dashboard interactif Streamlit

### Configuration
- `schedule_update.sh` - Configuration cron pour mardi 18h00
- `run_dashboard.sh` - Script de lancement du dashboard
- `requirements.txt` - Dépendances Python mises à jour

## 🚀 Utilisation

### Mise à jour automatique
```bash
# Configuration de la planification (une seule fois)
chmod +x schedule_update.sh
./schedule_update.sh

# Mise à jour manuelle
python3 update_data.py
```

### Dashboard
```bash
# Installation des dépendances
pip install -r requirements.txt

# Lancement du dashboard
chmod +x run_dashboard.sh
./run_dashboard.sh
```

## 📊 Fonctionnalités du Dashboard

- **Vue d'ensemble** : Métriques globales et comparaisons
- **Top 50/200 Année Courante** : Classements actuels
- **Année Précédente** : Comparaison avec l'année passée
- **Depuis 2020** : Analyse historique complète
- **Producteurs Constants** : Producteurs présents sur plusieurs années
- **Analyse Détaillée** : Évolution spécifique par producteur

## 🔄 Logique de Mise à Jour

- **Fréquence** : Chaque mardi à 18h00
- **Scope** : Année en cours uniquement (optimisé)
- **Nouvelle année** : Création automatique à la dernière semaine
- **Cache** : Évite les requêtes API redondantes