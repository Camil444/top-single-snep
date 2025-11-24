import psycopg2
from psycopg2 import sql
import pandas as pd
import os
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration de la base de données
DB_CONFIG = {
    "dbname": "db",
    "user": "db_user",
    "password": "db_password",
    "host": os.getenv("DB_HOST", "localhost"),
    "port": "5432"
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

def get_db_connection():
    """Établit une connexion à la base de données PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Erreur de connexion à la base de données: {e}")
        raise

def create_table_for_year(year):
    """Crée la table pour une année spécifique si elle n'existe pas"""
    table_name = f"top_singles_{year}"
    
    create_table_query = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {} (
            id SERIAL PRIMARY KEY,
            classement INTEGER,
            artiste TEXT,
            artiste_2 TEXT,
            artiste_3 TEXT,
            artiste_4 TEXT,
            titre TEXT,
            editeur TEXT,
            annee INTEGER,
            semaine INTEGER,
            producer_1 TEXT,
            producer_2 TEXT,
            writer_1 TEXT,
            writer_2 TEXT,
            release_date TEXT,
            sample_type TEXT,
            sample_from TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(annee, semaine, classement)
        );
    """).format(sql.Identifier(table_name))
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(create_table_query)
        conn.commit()
        logger.info(f"Table {table_name} vérifiée/créée avec succès.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur lors de la création de la table {table_name}: {e}")
    finally:
        cur.close()
        conn.close()

def insert_record(data_list, year):
    """
    Insère une liste de dictionnaires dans la table de l'année correspondante.
    Utilisé par update.py pour les nouvelles données.
    """
    if not data_list:
        return

    table_name = f"top_singles_{year}"
    
    # S'assurer que la table existe
    create_table_for_year(year)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Colonnes attendues (doivent correspondre aux clés du dictionnaire et à la table)
    columns = [
        'classement', 'artiste', 'artiste_2', 'artiste_3', 'artiste_4',
        'titre', 'editeur', 'annee', 'semaine', 
        'producer_1', 'producer_2', 'writer_1', 'writer_2', 
        'release_date', 'sample_type', 'sample_from'
    ]
    
    # Construction de la requête INSERT dynamique
    insert_query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT (annee, semaine, classement) DO NOTHING").format(
        sql.Identifier(table_name),
        sql.SQL(', ').join(map(sql.Identifier, columns)),
        sql.SQL(', ').join(sql.Placeholder() * len(columns))
    )
    
    inserted_count = 0
    try:
        for item in data_list:
            # Préparer les valeurs dans l'ordre des colonnes, avec gestion des None
            values = [item.get(col) for col in columns]
            cur.execute(insert_query, values)
            inserted_count += 1
        
        conn.commit()
        logger.info(f"Inséré {inserted_count} enregistrements dans {table_name}.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur lors de l'insertion dans {table_name}: {e}")
    finally:
        cur.close()
        conn.close()

def load_csvs_to_db():
    """Charge tous les fichiers CSV du dossier data/ dans la base de données"""
    csv_files = sorted(DATA_DIR.glob("top_singles_*.csv"))
    
    if not csv_files:
        logger.warning("Aucun fichier CSV trouvé dans le dossier data/")
        return

    for csv_file in csv_files:
        try:
            # Extraire l'année du nom de fichier (top_singles_2025.csv -> 2025)
            year = int(csv_file.stem.split('_')[-1])
            logger.info(f"Traitement du fichier {csv_file.name} pour l'année {year}...")
            
            # Lire le CSV avec pandas pour gérer facilement les NaN
            df = pd.read_csv(csv_file)
            
            # Remplacer les NaN par None (pour SQL NULL)
            df = df.where(pd.notnull(df), None)
            
            # Convertir en liste de dictionnaires
            data_list = df.to_dict('records')
            
            # Insérer dans la base
            insert_record(data_list, year)
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement de {csv_file.name}: {e}")

def get_last_scraped_week(year):
    """Récupère la dernière semaine présente en base pour une année donnée"""
    table_name = f"top_singles_{year}"
    
    # Vérifier si la table existe d'abord
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Vérifier l'existence de la table
    cur.execute("SELECT to_regclass(%s)", (table_name,))
    if cur.fetchone()[0] is None:
        cur.close()
        conn.close()
        return 0 # Table n'existe pas, donc semaine 0
        
    try:
        query = sql.SQL("SELECT MAX(semaine) FROM {}").format(sql.Identifier(table_name))
        cur.execute(query)
        result = cur.fetchone()
        last_week = result[0] if result and result[0] is not None else 0
        return last_week
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la dernière semaine pour {year}: {e}")
        return 0
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    # Si exécuté directement, charger les CSV existants
    logger.info("Démarrage du chargement initial des données CSV vers PostgreSQL...")
    load_csvs_to_db()
    logger.info("Chargement initial terminé.")