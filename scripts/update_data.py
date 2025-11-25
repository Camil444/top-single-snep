#!/usr/bin/env python3
"""
Script automatique de mise à jour des données musicales avec l'API Genius
Exécution programmée : Tous les jours à 11h00

Ce script enrichit les données du top musical avec :
- Producteurs (producer_1, producer_2)
- Auteurs (writer_1, writer_2)  
- Date de sortie (release_date)
- Informations sur les samples (sample_type, sample_from)
"""

import pandas as pd
import numpy as np
import lyricsgenius
import requests
import json
import os
import time
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_FILE = PROJECT_ROOT / "song_cache_v2.json"

# Chargement des variables d'environnement
if load_dotenv:
    # Essayer de charger depuis viz_dashboard/.env.local
    env_path = PROJECT_ROOT / 'viz_dashboard' / '.env.local'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Fallback sur .env à la racine si existant
        load_dotenv(PROJECT_ROOT / '.env')

# Utilisation d'une variable d'environnement pour le token (sécurité)
ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
if not ACCESS_TOKEN:
    logging.warning("GENIUS_ACCESS_TOKEN n'est pas défini dans les variables d'environnement.")

BASE_URL = "https://api.genius.com"

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / 'update_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OptimizedSongCache:
    """Cache intelligent pour éviter les requêtes API redondantes"""
    
    def __init__(self, cache_file=CACHE_FILE):
        self.cache_file = cache_file
        self.cache = self.load_cache()
        self.stats = {"hits": 0, "misses": 0, "api_calls": 0}
        self.unsaved_changes = 0  # Compteur de changements non sauvegardés

    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erreur lors du chargement du cache: {e}")
                return {}
        return {}
    
    def save_cache(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.info(f"Cache sauvegardé: {len(self.cache)} entrées")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du cache: {e}")
    
    def get_key(self, title, artist):
        """Normalise titre et artiste pour créer une clé unique"""
        import re
        title_clean = re.sub(r'[^\w\s]', '', title.lower().strip())
        artist_clean = re.sub(r'[^\w\s]', '', artist.lower().strip())
        return f"{title_clean}|{artist_clean}"
    
    def get(self, title, artist):
        key = self.get_key(title, artist)
        if key in self.cache:
            self.stats["hits"] += 1
            return self.cache[key]
        self.stats["misses"] += 1
        return None
    
    def set(self, title, artist, data):
        key = self.get_key(title, artist)
        if key not in self.cache:
            logger.debug(f"Ajout au cache: {key}")
        self.cache[key] = data
        self.unsaved_changes += 1
        
        # Sauvegarder tous les 10 changements
        if self.unsaved_changes >= 10:
            self.save_cache()
            self.unsaved_changes = 0

class GeniusDataEnricher:
    """Enrichisseur de données musicales via l'API Genius"""
    
    def __init__(self):
        self.genius = lyricsgenius.Genius(ACCESS_TOKEN)
        self.genius.timeout = 20  # Augmenter le timeout
        self.genius.retries = 3   # Ajouter des retries
        self.cache = OptimizedSongCache()
        
    def get_song_details(self, title, artist):
        """Récupère les détails d'une chanson depuis l'API Genius"""
        song_data = {
            "producer_1": None, "producer_2": None,
            "writer_1": None, "writer_2": None,
            "release_date": None,
            "sample_type": None,
            "sample_from": None
        }

        try:
            # Vérifier le cache d'abord
            cached_data = self.cache.get(title, artist)
            if cached_data:
                return cached_data

            # Recherche via API
            song = self.genius.search_song(title, artist)
            if not song:
                self.cache.set(title, artist, song_data)
                return song_data

            song_id = song.to_dict()['id']
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
            
            r = requests.get(f"{BASE_URL}/songs/{song_id}", headers=headers, timeout=20)
            
            if r.status_code != 200:
                self.cache.set(title, artist, song_data)
                return song_data

            s = r.json()["response"]["song"]

            # Producteurs
            producers = [p["name"] for p in s.get("producer_artists", [])][:2]
            for i, prod in enumerate(producers, 1):
                song_data[f"producer_{i}"] = prod

            # Auteurs
            writers = [w["name"] for w in s.get("writer_artists", [])][:2]
            for i, writer in enumerate(writers, 1):
                song_data[f"writer_{i}"] = writer

            # Date de sortie
            song_data["release_date"] = s.get("release_date")

            # Samples/Interpolations
            for rel in s.get("song_relationships", []):
                rel_type = rel.get("relationship_type", "").lower()
                songs = rel.get("songs", [])
                
                if songs and ("sample" in rel_type or "interpolat" in rel_type):
                    sample_song = songs[0]
                    title_s = sample_song.get("title", "")
                    artist_s = sample_song.get("primary_artist", {}).get("name", "")
                    song_data["sample_type"] = "sample" if "sample" in rel_type else "interpolation"
                    song_data["sample_from"] = f"{title_s} - {artist_s}" if artist_s else title_s
                    break

            # Sauvegarder en cache
            self.cache.set(title, artist, song_data)
            self.cache.stats["api_calls"] += 1
            
            # Rate limiting
            time.sleep(0.1)

        except Exception as e:
            logger.error(f"Erreur API pour {title} - {artist}: {e}")
            self.cache.set(title, artist, song_data)

        return song_data

class DataUpdater:
    """Gestionnaire de mise à jour des données musicales"""
    
    def __init__(self):
        self.enricher = GeniusDataEnricher()
        self.current_year = datetime.now().year
        self.current_week = datetime.now().isocalendar()[1]
        
    def load_yearly_data(self):
        """Charge les données de toutes les années disponibles"""
        df_dict = {}
        
        for year in range(2020, self.current_year + 1):
            file_path = DATA_DIR / f"top_singles_{year}.csv"
            if file_path.exists():
                df_dict[str(year)] = pd.read_csv(file_path)
                logger.info(f"Chargé: {len(df_dict[str(year)])} entrées pour {year}")
            else:
                logger.warning(f"Fichier manquant: {file_path}")
                
        return df_dict
    
    def should_update_to_new_year(self):
        """Détermine si on doit passer à la nouvelle année (dernière semaine)"""
        # Dernière semaine de l'année (généralement semaine 52 ou 53)
        total_weeks = datetime(self.current_year, 12, 31).isocalendar()[1]
        return self.current_week >= total_weeks - 1
    
    def prepare_new_year_structure(self):
        """Prépare la structure pour la nouvelle année"""
        next_year = self.current_year + 1
        new_file_path = DATA_DIR / f"top_singles_{next_year}.csv"
        
        if not new_file_path.exists():
            # Créer la structure de base pour la nouvelle année
            sample_df = pd.DataFrame(columns=[
                'classement', 'artiste', 'artiste_2', 'artiste_3', 'artiste_4',
                'titre', 'editeur', 'annee', 'semaine', 'producer_1', 'producer_2',
                'writer_1', 'writer_2', 'release_date', 'sample_type', 'sample_from'
            ])
            sample_df.to_csv(new_file_path, index=False)
            logger.info(f"Fichier créé pour {next_year}: {new_file_path}")
    
    def update_all_data(self, df_dict):
        """Met à jour les données de toutes les années si nécessaire"""
        
        required_columns = ['producer_1', 'producer_2', 'writer_1', 'writer_2', 'release_date', 'sample_type', 'sample_from']
        
        for year_str, df in df_dict.items():
            logger.info(f"Traitement année {year_str}: {len(df)} entrées")
            
            # Vérifier si les colonnes enrichies existent, sinon les créer
            for col in required_columns:
                if col not in df.columns:
                    df[col] = None
            
            # Identifier les entrées à enrichir (sans données producteur)
            entries_to_enrich = df[df['producer_1'].isna()]
            
            if len(entries_to_enrich) == 0:
                logger.info(f"Année {year_str}: Toutes les entrées sont déjà enrichies")
                continue
                
            logger.info(f"Année {year_str}: Enrichissement de {len(entries_to_enrich)} entrées")
            
            # Enrichissement (Correction du bug : appel API si absent du cache)
            processed = 0
            for idx, row in entries_to_enrich.iterrows():
                try:
                    # Appel à get_song_details qui gère Cache + API
                    song_data = self.enricher.get_song_details(row['titre'], row['artiste'])
                    
                    if song_data:
                        for col, val in song_data.items():
                            df.at[idx, col] = val
                        processed += 1
                        
                    if processed % 100 == 0: # Log plus fréquent pour suivre l'avancement
                        logger.info(f"Année {year_str}: Traité {processed}/{len(entries_to_enrich)}")
                        # Sauvegarde intermédiaire du cache pour ne pas tout perdre en cas de crash
                        if processed % 500 == 0:
                            self.enricher.cache.save_cache()
                        
                except Exception as e:
                    logger.error(f"Erreur ligne {idx} année {year_str}: {e}")
            
            logger.info(f"Année {year_str}: Enrichi {processed}/{len(entries_to_enrich)} entrées")
            
            # Sauvegarder les données enrichies
            output_path = DATA_DIR / f"top_singles_{year_str}.csv"
            df.to_csv(output_path, index=False)
            logger.info(f"Sauvegardé: {output_path}")
            
            df_dict[year_str] = df
        
        return df_dict
    
    def run_update(self):
        """Exécute la mise à jour complète"""
        logger.info("=== DÉBUT DE LA MISE À JOUR ===")
        logger.info(f"Date: {datetime.now()}")
        logger.info(f"Année courante: {self.current_year}, Semaine: {self.current_week}")
        
        try:
            # Chargement des données
            df_dict = self.load_yearly_data()
            
            # Vérifier si on doit préparer la nouvelle année
            if self.should_update_to_new_year():
                logger.info("Préparation de la structure pour la nouvelle année")
                self.prepare_new_year_structure()
            
            # Mise à jour de toutes les années
            df_dict = self.update_all_data(df_dict)
            
            # Statistiques finales
            self.enricher.cache.save_cache()
            logger.info(f"Statistiques cache: {self.enricher.cache.stats}")
            
            logger.info("=== MISE À JOUR TERMINÉE ===")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour: {e}")
            return False

def main():
    """Point d'entrée principal"""
    updater = DataUpdater()
    success = updater.run_update()
    
    if success:
        logger.info("✅ Mise à jour réussie")
        exit(0)
    else:
        logger.error("❌ Échec de la mise à jour")
        exit(1)

if __name__ == "__main__":
    main()