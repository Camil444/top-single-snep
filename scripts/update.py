import logging
import datetime
import os
from scrap import SNEPScraper
from update_data import GeniusDataEnricher
from insert_record import insert_record, get_last_scraped_week

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def enrich_data_list(data_list, enricher):
    """
    Enriches a list of dictionaries (SNEP data) with Genius data.
    """
    enriched_count = 0
    total = len(data_list)
    
    for i, item in enumerate(data_list, 1):
        try:
            # Progress log every 10 items
            if i % 10 == 0:
                logger.info(f"Enrichissement en cours... {i}/{total}")

            # Retrieve details via Genius (uses GeniusDataEnricher internal cache)
            song_details = enricher.get_song_details(item['titre'], item['artiste'])
            
            # Merge data
            if song_details:
                item.update(song_details)
                enriched_count += 1
                
        except Exception as e:
            # In case of error (timeout, etc.), we log but DO NOT BLOCK the process.
            # The item will be inserted without Genius data (NULL in database), which is better than nothing.
            logger.error(f"Erreur lors de l'enrichissement de {item.get('titre', '?')} - {item.get('artiste', '?')}: {e}")
            
    logger.info(f"Enrichi {enriched_count}/{len(data_list)} entrées.")
    return data_list

def update_database():
    """
    Main update function:
    1. Determine current week.
    2. Check last week in database.
    3. Scrape, enrich and insert missing weeks.
    """
    current_date = datetime.datetime.now()
    current_year = int(os.getenv("TARGET_YEAR", current_date.year))
    # Si TARGET_WEEK est défini, on l'utilise, sinon on prend la semaine actuelle
    target_week_env = os.getenv("TARGET_WEEK")
    if target_week_env:
        current_week = int(target_week_env)
    else:
        current_week = current_date.isocalendar()[1]
    
    logger.info(f"Démarrage de la mise à jour. Année cible: {current_year}, Semaine cible: {current_week}")
    
    # Initialiser l'enrichisseur (charge le cache)
    enricher = GeniusDataEnricher()
    
    # Initialiser le scraper
    scraper = SNEPScraper()
    
    # On peut vouloir remonter un peu en arrière si on est en début d'année pour finir l'année précédente
    # Pour simplifier, on regarde l'année courante. 
    # Si on est semaine 1, on pourrait vouloir vérifier l'année d'avant, mais restons simple pour l'instant.
    
    last_db_week = get_last_scraped_week(current_year)
    logger.info(f"Dernière semaine en base pour {current_year}: {last_db_week}")
    
    if last_db_week >= current_week:
        logger.info("La base de données est à jour.")
        return

    # Boucle sur les semaines manquantes
    # On commence à last_db_week + 1
    # On va jusqu'à current_week inclus (ou exclus selon la dispo des données SNEP, mais scrape_week gère les erreurs)
    
    for week in range(last_db_week + 1, current_week + 1):
        logger.info(f"Traitement de la semaine {week}/{current_year}...")
        
        # 1. Scraping
        try:
            raw_data = scraper.scrape_week(current_year, week)
            if not raw_data:
                logger.warning(f"Aucune donnée récupérée pour la semaine {week}. Arrêt ou passage à la suivante.")
                continue
                
            logger.info(f"Récupéré {len(raw_data)} entrées depuis SNEP.")
            
            # 2. Enrichissement
            enriched_data = enrich_data_list(raw_data, enricher)
            
            # 3. Insertion
            insert_record(enriched_data, current_year)
            
            # Sauvegarder le cache Genius périodiquement
            enricher.cache.save_cache()
            
        except Exception as e:
            logger.error(f"Erreur critique lors du traitement de la semaine {week}: {e}")
            # On continue pour essayer les autres semaines ? Ou on break ?
            # Mieux vaut continuer au cas où c'est juste une semaine qui bug.
            continue

    logger.info("Mise à jour terminée.")

if __name__ == "__main__":
    update_database()
