import logging
import datetime
import os
from scrap import SNEPScraper
from update_data import GeniusDataEnricher
from insert_record import insert_record, get_last_scraped_week
from send_recap import send_recap_email

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def enrich_data_list(data_list, enricher):
    """
    Enriches a list of dictionaries (SNEP data) with Genius data.
    Returns (data_list, genius_error_count).
    """
    enriched_count = 0
    genius_errors = 0
    total = len(data_list)

    for i, item in enumerate(data_list, 1):
        try:
            if i % 10 == 0:
                logger.info(f"Enrichissement en cours... {i}/{total}")

            song_details = enricher.get_song_details(item['titre'], item['artiste'])

            if song_details:
                item.update(song_details)
                enriched_count += 1

        except Exception as e:
            genius_errors += 1
            logger.warning(f"Genius indisponible pour {item.get('titre', '?')} - {item.get('artiste', '?')}: {e}")

    logger.info(f"Enrichi {enriched_count}/{total} entrees ({genius_errors} echecs Genius).")
    return data_list, genius_errors

def update_database():
    """
    Main update function:
    1. Determine current week.
    2. Check last week in database.
    3. Scrape, enrich and insert missing weeks.
    4. Send recap email.
    """
    start_time = datetime.datetime.now()
    report = {
        "year": 0,
        "weeks_processed": [],
        "total_entries": 0,
        "errors": [],
        "warnings": [],
        "genius_errors": 0,
        "start_time": start_time,
        "end_time": start_time,
        "already_up_to_date": False,
    }

    current_date = datetime.datetime.now()
    current_year = int(os.getenv("TARGET_YEAR", current_date.year))
    target_week_env = os.getenv("TARGET_WEEK")
    if target_week_env:
        current_week = int(target_week_env)
    else:
        current_week = current_date.isocalendar()[1]

    report["year"] = current_year
    logger.info(f"Démarrage de la mise à jour. Année cible: {current_year}, Semaine cible: {current_week}")

    # Initialiser l'enrichisseur (charge le cache)
    enricher = GeniusDataEnricher()

    # Initialiser le scraper
    scraper = SNEPScraper()

    last_db_week = get_last_scraped_week(current_year)
    logger.info(f"Dernière semaine en base pour {current_year}: {last_db_week}")

    if last_db_week >= current_week:
        logger.info("La base de données est à jour.")
        report["already_up_to_date"] = True
        report["end_time"] = datetime.datetime.now()
        send_recap_email(report)
        return

    for week in range(last_db_week + 1, current_week + 1):
        logger.info(f"Traitement de la semaine {week}/{current_year}...")

        try:
            raw_data = scraper.scrape_week(current_year, week)
            if not raw_data:
                logger.warning(f"Aucune donnée récupérée pour la semaine {week}.")
                report["warnings"].append(f"Semaine {week}: pas encore disponible sur le SNEP")
                continue

            logger.info(f"Récupéré {len(raw_data)} entrées depuis SNEP.")

            enriched_data, genius_errs = enrich_data_list(raw_data, enricher)
            insert_record(enriched_data, current_year)
            enricher.cache.save_cache()

            report["weeks_processed"].append(week)
            report["total_entries"] += len(enriched_data)
            report["genius_errors"] += genius_errs

        except Exception as e:
            error_msg = f"Semaine {week}: {e}"
            logger.error(f"Erreur critique lors du traitement de la semaine {week}: {e}")
            report["errors"].append(error_msg)
            continue

    report["end_time"] = datetime.datetime.now()
    logger.info("Mise à jour terminée.")
    send_recap_email(report)

if __name__ == "__main__":
    update_database()
