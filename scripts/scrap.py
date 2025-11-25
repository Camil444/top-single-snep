#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scraper to retrieve Top Singles data from SNEP Musique
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import os
from urllib.parse import urljoin
import logging
from datetime import datetime
import re
import urllib3
import json

# Disable insecure SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Parsing utility functions (extracted for modularity and testing) ---

def parse_artists_in_feat(artistes_text):
    """
    Parse artists in a feat. (can contain &, commas, etc.)
    """
    if not artistes_text:
        return []
    
    # Split by & and commas
    artistes = re.split(r'\s*[&,]\s*', artistes_text)
    return [a.strip() for a in artistes if a.strip()]

def handle_x_separator(text):
    """
    Smartly handles X as an artist separator
    """
    # Pattern to detect an X surrounded by spaces between words that look like names
    # We look for: [Word(s)] X [Word(s)] where words start with a capital letter
    x_pattern = r'\b([A-Z][A-Za-z\s]+?)\s+X\s+([A-Z][A-Za-z\s]+?)\b'
    
    def replace_x(match):
        artist1 = match.group(1).strip()
        artist2 = match.group(2).strip()
        
        # Additional checks to ensure they are artist names
        # Avoid replacing if words are too short or contain suspicious characters
        if (len(artist1) >= 2 and len(artist2) >= 2 and 
            not re.search(r'\d{3,}', artist1 + artist2) and  # Avoid long numbers
            not re.search(r'\b(THE|AND|OF|FOR|WITH|IN|ON|AT)\b', artist1 + " " + artist2, re.IGNORECASE)):
            return f"{artist1}|SEPARATOR|{artist2}"
        else:
            # Return original text if it doesn't look like artist names
            return match.group(0)
    
    return re.sub(x_pattern, replace_x, text)

def parse_artists(artiste_string):
    """
    Separates multiple artists based on delimiters: comma, FEAT., &, X (smart)
    
    Args:
        artiste_string: String potentially containing multiple artists
        
    Returns:
        Dict with artiste, artiste_2, artiste_3, artiste_4
    """
    result = {
        'artiste': '',
        'artiste_2': '',
        'artiste_3': '',
        'artiste_4': ''
    }
    
    if not artiste_string or artiste_string.strip() == '':
        return result
    
    # Clean the string
    cleaned_string = artiste_string.strip()
    
    # Replace different separators with a uniform separator
    # We use |SEPARATOR| as a unique temporary delimiter
    
    # Pattern for FT/FEAT (case insensitive)
    # \s+ ensures at least one space before.
    # (?:FT|FEAT) matches the keyword.
    # (?:\.|\b) matches a dot OR a word boundary.
    # \s* matches optional space after.
    pattern_feat = r'\s+(?:FT|FEAT)(?:\.|\b)\s*'
    cleaned_string = re.sub(pattern_feat, '|SEPARATOR|', cleaned_string, flags=re.IGNORECASE)
    
    # Pattern for & (surrounded by optional spaces)
    cleaned_string = re.sub(r'\s*&\s*', '|SEPARATOR|', cleaned_string)
    
    # Pattern for comma
    cleaned_string = re.sub(r'\s*,\s*', '|SEPARATOR|', cleaned_string)
    
    # Smart handling of X as separator
    cleaned_string = handle_x_separator(cleaned_string)
    
    # Split by uniform delimiter
    artists = [artist.strip() for artist in cleaned_string.split('|SEPARATOR|') if artist.strip()]
    
    # Assign to columns
    keys = ['artiste', 'artiste_2', 'artiste_3', 'artiste_4']
    for i, artist in enumerate(artists[:4]):  # Maximum 4 artists
        if i < len(keys):
            result[keys[i]] = artist
    
    return result

def clean_title_and_extract_feat(titre):
    """
    Cleans the title by removing parentheses and extracts feat. artists.
    
    Args:
        titre: Original title
        
    Returns:
        Tuple (clean_title, list_feat_artists)
    """
    if not titre:
        return titre, []
    
    titre_propre = titre.strip()
    artistes_feat = []
    
    # Search for content inside parentheses
    parentheses_pattern = r'\(([^)]+)\)'
    matches = re.findall(parentheses_pattern, titre_propre)
    
    for match in matches:
        # Check if it is a feat.
        if re.search(r'\b(feat\.?|ft\.?|featuring)\b', match, re.IGNORECASE):
            # Extract artists after feat.
            feat_pattern = r'\b(?:feat\.?|ft\.?|featuring)\s+(.+)'
            feat_match = re.search(feat_pattern, match, re.IGNORECASE)
            if feat_match:
                artistes_text = feat_match.group(1).strip()
                # Separate artists in the feat.
                artistes_dans_feat = parse_artists_in_feat(artistes_text)
                artistes_feat.extend(artistes_dans_feat)
    
    # Remove all parentheses from the title
    titre_propre = re.sub(r'\s*\([^)]*\)\s*', ' ', titre_propre)
    titre_propre = re.sub(r'\s+', ' ', titre_propre).strip()
    
    return titre_propre, artistes_feat

def merge_artists(artists_data, feat_artists):
    """
    Merges main artists with feat. artists without duplicates
    """
    # Collect all existing artists
    existing_artists = []
    for key in ['artiste', 'artiste_2', 'artiste_3', 'artiste_4']:
        if artists_data[key]:
            existing_artists.append(artists_data[key].upper())
    
    # Add feat. artists if they are not already present
    keys = ['artiste', 'artiste_2', 'artiste_3', 'artiste_4']
    for feat_artist in feat_artists:
        if feat_artist.upper() not in existing_artists:
            # Find the next empty column
            for key in keys:
                if not artists_data[key]:
                    artists_data[key] = feat_artist
                    existing_artists.append(feat_artist.upper())
                    break
    
    return artists_data

# --- Fin des fonctions utilitaires ---

class SNEPScraper:
    def __init__(self, delay_between_requests=1.5):
        """
        Initializes the SNEP scraper
        
        Args:
            delay_between_requests: Delay in seconds between each request
        """
        self.base_url = "https://snepmusique.com/les-tops/le-top-de-la-semaine/top-albums/"
        self.delay = delay_between_requests
        self.session = requests.Session()
        # Disable SSL verification to avoid local certificate errors
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Create data folder if it doesn't exist
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"Folder '{self.data_dir}' created")

        # Cache initialization
        self.cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'snep_scrap_cache.json')
        self.cache = self.load_cache()

    def load_cache(self):
        """Loads cache from JSON file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    logger.info(f"Loading cache from {self.cache_file}")
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
                return {}
        return {}

    def save_cache(self):
        """Saves cache to JSON file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.info("Cache updated")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def clean_title_and_extract_feat(self, titre):
        return clean_title_and_extract_feat(titre)
    
    def parse_artists_in_feat(self, artistes_text):
        return parse_artists_in_feat(artistes_text)
    
    def parse_artists(self, artiste_string):
        return parse_artists(artiste_string)
    
    def handle_x_separator(self, text):
        return handle_x_separator(text)
    
    def merge_artists(self, artists_data, feat_artists):
        return merge_artists(artists_data, feat_artists)
    
    def get_page_content(self, semaine, annee):
        """
        Retrieves HTML content of a page for a given week
        
        Args:
            semaine: Week number
            annee: Year
            
        Returns:
            BeautifulSoup object or None if error
        """
        params = {
            'categorie': 'Top Singles',
            'semaine': str(semaine),
            'annee': str(annee)
        }
        
        try:
            logger.info(f"Retrieving data: Year {annee}, Week {semaine}")
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.error(f"Error retrieving page (Year {annee}, Week {semaine}): {e}")
            return None
    
    def extract_data_from_page(self, soup, semaine, annee):
        """
        Extracts data from the page
        
        Args:
            soup: BeautifulSoup object
            semaine: Week number
            annee: Year
            
        Returns:
            List of dictionaries containing the data
        """
        data = []
        
        if not soup:
            return data
        
        try:
            # Search for main container with articles
            # Data can be in articles or divs with class 'item'
            items = soup.find_all('article', class_='classement-item')
            
            if not items:
                # Alternative: search for divs with class item
                items = soup.find_all('div', class_='item')
            
            if not items:
                # Another alternative: search in div.items structure
                items_container = soup.find('div', class_='items')
                if items_container:
                    items = items_container.find_all(['article', 'div'], recursive=False)
            
            if not items:
                # Last attempt: search all structures that look like ranking items
                main_content = soup.find(['main', 'div'], id=['primary', 'content', 'main-content'])
                if main_content:
                    # Search for data blocks
                    items = []
                    
                    # Pattern to identify ranking blocks
                    classement_blocks = main_content.find_all(['div', 'article'], 
                                                             class_=re.compile(r'(item|single|track|classement)', re.I))
                    
                    for block in classement_blocks:
                        # Check if it is indeed a ranking item
                        if block.find(text=re.compile(r'^\d+$|^\d+e?La Semaine', re.I)):
                            items.append(block)
            
            logger.info(f"Number of items found: {len(items)}")
            
            for item in items:
                try:
                    item_data = {}
                    
                    # Extract ranking (number at the beginning or in a specific tag)
                    classement = None
                    
                    # PRIORITY 1: Specifically search for class "rang" (SNEP standard)
                    # Explicitly exclude "rang_precedent"
                    classement_elem = item.find('div', class_='rang')
                    if classement_elem:
                        classement_text = classement_elem.get_text(strip=True)
                        match = re.search(r'(\d+)', classement_text)
                        if match:
                            classement = match.group(1)

                    # PRIORITY 2: If not found, search with regex but excluding "precedent"
                    if not classement:
                        # Search for classes matching rank/position/etc...
                        candidates = item.find_all(['span', 'div', 'strong'], class_=re.compile(r'(rank|position|classement|number)', re.I))
                        
                        for candidate in candidates:
                            # Check that class does not contain "precedent" or "previous"
                            classes = candidate.get('class', [])
                            class_str = " ".join(classes).lower()
                            
                            if 'precedent' in class_str or 'previous' in class_str or 'last' in class_str:
                                continue
                                
                            classement_text = candidate.get_text(strip=True)
                            match = re.search(r'(\d+)', classement_text)
                            if match:
                                classement = match.group(1)
                                break
                    
                    if not classement:
                        # Search in item text (fallback)
                        text = item.get_text(strip=True)
                        match = re.match(r'^(\d+)', text)
                        if match:
                            classement = match.group(1)
                    
                    
                    # Extract title, artist and label
                    # These information can be in different tags
                    
                    # Method 1: Search for specific tags
                    titre_elem = item.find(['h2', 'h3', 'h4', 'h5', 'span', 'div'], 
                                          class_=re.compile(r'(title|titre|song|track)', re.I))
                    artiste_elem = item.find(['span', 'div', 'p'], 
                                            class_=re.compile(r'(artist|artiste|performer)', re.I))
                    editeur_elem = item.find(['span', 'div', 'p'], 
                                            class_=re.compile(r'(label|editeur|publisher|producer)', re.I))
                    
                    titre = titre_elem.get_text(strip=True) if titre_elem else None
                    artiste = artiste_elem.get_text(strip=True) if artiste_elem else None
                    editeur = editeur_elem.get_text(strip=True) if editeur_elem else None
                    
                    # Method 2: If not found, try to parse full text
                    if not all([titre, artiste, editeur]):
                        # Get all text and split intelligently
                        lines = []
                        for elem in item.find_all(text=True):
                            text = elem.strip()
                            if text and not re.match(r'^(\d+e?La Semaine|Nouveau)', text, re.I):
                                lines.append(text)
                        
                        # Filter lines to remove ranking and week info
                        filtered_lines = []
                        for line in lines:
                            if not re.match(r'^\d+$', line) and len(line) > 2:
                                filtered_lines.append(line)
                        
                        # Generally: Title, Artist, Label
                        if len(filtered_lines) >= 3:
                            titre = titre or filtered_lines[0]
                            artiste = artiste or filtered_lines[1]
                            editeur = editeur or filtered_lines[2]
                        elif len(filtered_lines) == 2:
                            titre = titre or filtered_lines[0]
                            artiste = artiste or filtered_lines[1]
                        elif len(filtered_lines) == 1:
                            titre = titre or filtered_lines[0]
                    
                    # If we have at least ranking and title, add entry
                    if classement and titre:
                        # Clean title and extract feat.
                        titre_propre, feat_artists = self.clean_title_and_extract_feat(titre)
                        
                        # Parse multiple artists
                        artists_data = self.parse_artists(artiste or '')
                        
                        # Merge with feat. artists
                        artists_data = self.merge_artists(artists_data, feat_artists)
                        
                        entry = {
                            'classement': classement,
                            'artiste': artists_data['artiste'],
                            'artiste_2': artists_data['artiste_2'],
                            'artiste_3': artists_data['artiste_3'],
                            'artiste_4': artists_data['artiste_4'],
                            'titre': titre_propre,
                            'editeur': editeur or '',
                            'annee': annee,
                            'semaine': semaine
                        }
                        data.append(entry)
                        logger.debug(f"Entry added: {entry}")
                    
                except Exception as e:
                    logger.error(f"Error extracting item: {e}")
                    continue
            
            # If no item found with structured method,
            # try text-based extraction
            if len(data) == 0:
                logger.info("Attempting alternative text-based extraction...")
                data = self.extract_data_from_text(soup, semaine, annee)
            
            logger.info(f"Number of entries extracted: {len(data)}")
            
        except Exception as e:
            logger.error(f"Error extracting data: {e}")
        
        return data
    
    def extract_data_from_text(self, soup, semaine, annee):
        """
        Alternative method to extract data based on text analysis
        """
        data = []
        
        try:
            # Get all text from the page
            text_content = soup.get_text()
            
            # Split into lines and clean
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            
            # Pattern to identify a ranking number
            classement_pattern = re.compile(r'^(\d{1,3})$')
            
            i = 0
            while i < len(lines):
                # Search for a ranking number
                if classement_pattern.match(lines[i]):
                    classement = lines[i]
                    
                    # Following lines should be title, artist, label
                    titre = None
                    artiste = None
                    editeur = None
                    
                    j = i + 1
                    collected_lines = []
                    
                    # Collect next lines until next ranking or indicator
                    while j < len(lines) and not classement_pattern.match(lines[j]):
                        line = lines[j]
                        # Ignore navigation and metadata lines
                        if not any(skip in line.lower() for skip in ['semaine', 'nouveau', 'télécharger', 'pdf', 'précédente', 'suivante']):
                            # Also ignore last week's positions
                            if not re.match(r'^\d+e?La Semaine', line, re.I):
                                collected_lines.append(line)
                        j += 1
                    
                    # Assign collected lines
                    if len(collected_lines) >= 1:
                        titre = collected_lines[0]
                    if len(collected_lines) >= 2:
                        artiste = collected_lines[1]
                    if len(collected_lines) >= 3:
                        editeur = collected_lines[2]
                    
                    # Add entry if we have at least a title
                    if titre:
                        # Clean title and extract feat.
                        titre_propre, feat_artists = self.clean_title_and_extract_feat(titre)
                        
                        # Parse multiple artists
                        artists_data = self.parse_artists(artiste or '')
                        
                        # Merge with feat. artists
                        artists_data = self.merge_artists(artists_data, feat_artists)
                        
                        entry = {
                            'classement': classement,
                            'artiste': artists_data['artiste'],
                            'artiste_2': artists_data['artiste_2'],
                            'artiste_3': artists_data['artiste_3'],
                            'artiste_4': artists_data['artiste_4'],
                            'titre': titre_propre,
                            'editeur': editeur or '',
                            'annee': annee,
                            'semaine': semaine
                        }
                        data.append(entry)
                    
                    i = j
                else:
                    i += 1
        
        except Exception as e:
            logger.error(f"Error during alternative extraction: {e}")
        
        return data
    
    def save_to_csv(self, data, annee):
        """
        Saves data to a CSV file
        
        Args:
            data: List of dictionaries containing the data
            annee: Year for the filename
        """
        if not data:
            logger.warning(f"No data to save for year {annee}")
            return
        
        filename = os.path.join(self.data_dir, f"top_singles_{annee}.csv")
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['classement', 'artiste', 'artiste_2', 'artiste_3', 'artiste_4', 'titre', 'editeur', 'annee', 'semaine']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
            
            logger.info(f"Data saved in {filename} ({len(data)} entries)")
        except Exception as e:
            logger.error(f"Error saving CSV: {e}")
    
    def scrape_week(self, annee, semaine):
        """
        Scrapes a specific week and returns the data (without saving to CSV)
        
        Args:
            annee: Year to scrape
            semaine: Week to scrape
            
        Returns:
            List of dictionaries containing the data
        """
        cache_key = f"{annee}_{semaine}"
        
        # Check cache
        if cache_key in self.cache:
            logger.info(f"Data retrieved from cache for Year {annee}, Week {semaine}")
            return self.cache[cache_key]

        logger.info(f"Retrieving data: Year {annee}, Week {semaine}")
        
        soup = self.get_page_content(semaine, annee)
        if not soup:
            logger.warning(f"✗ Year {annee}, Week {semaine} : No data found (Request error)")
            return []
            
        data = self.extract_data_from_page(soup, semaine, annee)
        
        if data:
            logger.info(f"✓ Year {annee}, Week {semaine} : {len(data)} entries retrieved")
            # Update cache
            self.cache[cache_key] = data
            # Save cache periodically (here after each successful week to avoid losing everything)
            # To optimize, we could save less often, but this is safer.
            # self.save_cache() -> Can be done at the end of the year or here. 
            # Let's do it here for now to be safe.
            return data
        else:
            logger.warning(f"✗ Year {annee}, Week {semaine} : No data found")
            return []

    def scrape_year(self, annee, semaine_debut, semaine_fin):
        """
        Scrapes all weeks of a year
        
        Args:
            annee: Year to scrape
            semaine_debut: First week to scrape
            semaine_fin: Last week to scrape
        """
        logger.info(f"Starting scraping for year {annee} (weeks {semaine_debut} to {semaine_fin})")
        all_data = []
        semaines_manquantes = []
        
        for semaine in range(semaine_debut, semaine_fin + 1):
            data = self.scrape_week(annee, semaine)
            
            if data:
                all_data.extend(data)
            else:
                semaines_manquantes.append(semaine)
            
            # Pause between requests only if we didn't use cache
            # If coming from cache, it's instant, no need to sleep
            if f"{annee}_{semaine}" not in self.cache:
                time.sleep(self.delay)
        
        # Save cache at the end of the year to limit disk writes
        self.save_cache()

        # Save all data for the year
        if all_data:
            self.save_to_csv(all_data, annee)
        
        # Log missing weeks
        if semaines_manquantes:
            logger.warning(f"Missing weeks for {annee}: {semaines_manquantes}")
        
        return all_data
    
    def clean_existing_csv_files(self):
        """
        Deletes existing CSV files to regenerate them
        """
        years = [2020, 2021, 2022, 2023, 2024, 2025]
        deleted_files = []
        
        for year in years:
            filename = os.path.join(self.data_dir, f"top_singles_{year}.csv")
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                    deleted_files.append(filename)
                    logger.info(f"File deleted: {filename}")
                except Exception as e:
                    logger.error(f"Error deleting {filename} : {e}")
        
        if deleted_files:
            logger.info(f"Deletion complete: {len(deleted_files)} files deleted")
        else:
            logger.info("No existing CSV files to delete")
    
    def run(self):
        """
        Starts the full scraping process
        """
        logger.info("=" * 50)
        logger.info("Starting SNEP scraper")
        logger.info("=" * 50)
        
        # NOTE: Automatic deletion disabled to avoid data loss
        # self.clean_existing_csv_files()
        
        # Dynamic calculation of current week
        now = datetime.now()
        current_year = now.year
        current_week = now.isocalendar()[1]
        
        # Scrape current year (2025)
        if current_year == 2025:
            # Go up to previous week to ensure data is published
            # Or up to current week if we want to try
            limit_week = current_week - 1 if current_week > 1 else 1
            
            # For the requested test, force up to 45 if beyond, or use dynamic logic
            # Here I respect the user's explicit request to go up to 45 for the test
            limit_week = 45 
            
            logger.info(f"Scraping current year {current_year} up to week {limit_week}")
            data_2025 = self.scrape_year(2025, 1, limit_week)
            logger.info(f"Total 2025 : {len(data_2025)} entries")
        
        # Scrape previous years only if necessary
        for year in range(2024, 2019, -1):
            # Force scraping even if file exists because we want to fix rankings
            logger.info(f"Starting scraping for {year}...")
            data_year = self.scrape_year(year, 1, 52)
            logger.info(f"Total {year} : {len(data_year)} entries")
        
        logger.info("=" * 50)
        logger.info("Scraping finished!")
        logger.info("=" * 50)


def main():
    """
    Main function
    """
    print("""
    ╔══════════════════════════════════════════╗
    ║     SNEP Top Singles Scraper            ║
    ║     Retrieving data...                  ║
    ╚══════════════════════════════════════════╝
    """)
    
    # Create and run scraper
    scraper = SNEPScraper(delay_between_requests=1.5)
    
    try:
        scraper.run()
        print("\n✅ Scraping completed successfully!")
        print("📁 CSV files have been saved in the 'data' folder")
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        logger.error(f"Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    main()