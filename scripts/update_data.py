#!/usr/bin/env python3
"""
Automatic script to update music data with the Genius API
Scheduled execution: Every day at 11:00 AM

This script enriches the top music data with:
- Producers (producer_1, producer_2)
- Writers (writer_1, writer_2)
- Release date (release_date)
- Sample information (sample_type, sample_from)
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

# Load environment variables
if load_dotenv:
    # Try to load from viz_dashboard/.env.local
    env_path = PROJECT_ROOT / 'viz_dashboard' / '.env.local'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Fallback to root .env if it exists
        load_dotenv(PROJECT_ROOT / '.env')

# Use an environment variable for the token (security)
ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
if not ACCESS_TOKEN:
    logging.warning("GENIUS_ACCESS_TOKEN is not defined in environment variables.")

BASE_URL = "https://api.genius.com"

# Logging configuration
handlers = [logging.StreamHandler()]
try:
    handlers.append(logging.FileHandler(PROJECT_ROOT / 'update_data.log'))
except (PermissionError, OSError):
    pass  # Fallback to stdout only if file write fails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

class OptimizedSongCache:
    """Smart cache to avoid redundant API requests"""
    
    def __init__(self, cache_file=CACHE_FILE):
        self.cache_file = cache_file
        self.cache = self.load_cache()
        self.stats = {"hits": 0, "misses": 0, "api_calls": 0}
        self.unsaved_changes = 0  # Counter for unsaved changes

    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
                return {}
        return {}
    
    def save_cache(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.info(f"Cache saved: {len(self.cache)} entries")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def get_key(self, title, artist):
        """Normalizes title and artist to create a unique key"""
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
            logger.debug(f"Adding to cache: {key}")
        self.cache[key] = data
        self.unsaved_changes += 1
        
        # Save every 10 changes
        if self.unsaved_changes >= 10:
            self.save_cache()
            self.unsaved_changes = 0

class GeniusDataEnricher:
    """Music data enricher via Genius API"""
    
    def __init__(self):
        self.genius = lyricsgenius.Genius(ACCESS_TOKEN)
        self.genius.timeout = 20  # Increase timeout
        self.genius.retries = 3   # Add retries
        self.cache = OptimizedSongCache()
        
    def get_song_details(self, title, artist):
        """Retrieves song details from Genius API"""
        song_data = {
            "producer_1": None, "producer_2": None,
            "writer_1": None, "writer_2": None,
            "release_date": None,
            "sample_type": None,
            "sample_from": None
        }

        try:
            # Check cache first
            cached_data = self.cache.get(title, artist)
            if cached_data:
                return cached_data

            # Search via API
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

            # Producers
            producers = [p["name"] for p in s.get("producer_artists", [])][:2]
            for i, prod in enumerate(producers, 1):
                song_data[f"producer_{i}"] = prod

            # Writers
            writers = [w["name"] for w in s.get("writer_artists", [])][:2]
            for i, writer in enumerate(writers, 1):
                song_data[f"writer_{i}"] = writer

            # Release date
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

            # Save to cache
            self.cache.set(title, artist, song_data)
            self.cache.stats["api_calls"] += 1
            
            # Rate limiting
            time.sleep(0.1)

        except Exception as e:
            logger.error(f"API Error for {title} - {artist}: {e}")
            self.cache.set(title, artist, song_data)

        return song_data

class DataUpdater:
    """Music data update manager"""
    
    def __init__(self):
        self.enricher = GeniusDataEnricher()
        self.current_year = datetime.now().year
        self.current_week = datetime.now().isocalendar()[1]
        
    def load_yearly_data(self):
        """Loads data for all available years"""
        df_dict = {}
        
        for year in range(2020, self.current_year + 1):
            file_path = DATA_DIR / f"top_singles_{year}.csv"
            if file_path.exists():
                df_dict[str(year)] = pd.read_csv(file_path)
                logger.info(f"Loaded: {len(df_dict[str(year)])} entries for {year}")
            else:
                logger.warning(f"Missing file: {file_path}")
                
        return df_dict
    
    def should_update_to_new_year(self):
        """Determines if we should switch to the new year (last week)"""
        # Last week of the year (usually week 52 or 53)
        total_weeks = datetime(self.current_year, 12, 31).isocalendar()[1]
        return self.current_week >= total_weeks - 1
    
    def prepare_new_year_structure(self):
        """Prepares structure for the new year"""
        next_year = self.current_year + 1
        new_file_path = DATA_DIR / f"top_singles_{next_year}.csv"
        
        if not new_file_path.exists():
            # Create basic structure for the new year
            sample_df = pd.DataFrame(columns=[
                'classement', 'artiste', 'artiste_2', 'artiste_3', 'artiste_4',
                'titre', 'editeur', 'annee', 'semaine', 'producer_1', 'producer_2',
                'writer_1', 'writer_2', 'release_date', 'sample_type', 'sample_from'
            ])
            sample_df.to_csv(new_file_path, index=False)
            logger.info(f"File created for {next_year}: {new_file_path}")
    
    def update_all_data(self, df_dict):
        """Updates data for all years if necessary"""
        
        required_columns = ['producer_1', 'producer_2', 'writer_1', 'writer_2', 'release_date', 'sample_type', 'sample_from']
        
        for year_str, df in df_dict.items():
            logger.info(f"Processing year {year_str}: {len(df)} entries")
            
            # Check if enriched columns exist, otherwise create them
            for col in required_columns:
                if col not in df.columns:
                    df[col] = None
            
            # Identify entries to enrich (missing producer data)
            entries_to_enrich = df[df['producer_1'].isna()]
            
            if len(entries_to_enrich) == 0:
                logger.info(f"Year {year_str}: All entries are already enriched")
                continue
                
            logger.info(f"Year {year_str}: Enriching {len(entries_to_enrich)} entries")
            
            # Enrichment (Bug fix: API call if missing from cache)
            processed = 0
            for idx, row in entries_to_enrich.iterrows():
                try:
                    # Call get_song_details which handles Cache + API
                    song_data = self.enricher.get_song_details(row['titre'], row['artiste'])
                    
                    if song_data:
                        for col, val in song_data.items():
                            df.at[idx, col] = val
                        processed += 1
                        
                    if processed % 100 == 0: # More frequent log to track progress
                        logger.info(f"Year {year_str}: Processed {processed}/{len(entries_to_enrich)}")
                        # Intermediate cache save to avoid losing everything in case of crash
                        if processed % 500 == 0:
                            self.enricher.cache.save_cache()
                        
                except Exception as e:
                    logger.error(f"Error line {idx} year {year_str}: {e}")
            
            logger.info(f"Year {year_str}: Enriched {processed}/{len(entries_to_enrich)} entries")
            
            # Save enriched data
            output_path = DATA_DIR / f"top_singles_{year_str}.csv"
            df.to_csv(output_path, index=False)
            logger.info(f"Saved: {output_path}")
            
            df_dict[year_str] = df
        
        return df_dict
    
    def run_update(self):
        """Executes full update"""
        logger.info("=== STARTING UPDATE ===")
        logger.info(f"Date: {datetime.now()}")
        logger.info(f"Current year: {self.current_year}, Week: {self.current_week}")
        
        try:
            # Load data
            df_dict = self.load_yearly_data()
            
            # Check if we need to prepare for the new year
            if self.should_update_to_new_year():
                logger.info("Preparing structure for the new year")
                self.prepare_new_year_structure()
            
            # Update all years
            df_dict = self.update_all_data(df_dict)
            
            # Final statistics
            self.enricher.cache.save_cache()
            logger.info(f"Cache statistics: {self.enricher.cache.stats}")
            
            logger.info("=== UPDATE COMPLETED ===")
            return True
            
        except Exception as e:
            logger.error(f"Error during update: {e}")
            return False

def main():
    """Main entry point"""
    updater = DataUpdater()
    success = updater.run_update()
    
    if success:
        logger.info("✅ Update successful")
        exit(0)
    else:
        logger.error("❌ Update failed")
        exit(1)

if __name__ == "__main__":
    main()