import psycopg2
from psycopg2 import sql
import os
import logging

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

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Erreur de connexion à la base de données: {e}")
        raise

def reset_database():
    conn = get_db_connection()
    cur = conn.cursor()
    
    years = range(2020, 2027)
    
    for year in years:
        table_name = f"top_singles_{year}"
        try:
            cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(table_name)))
            logger.info(f"Table {table_name} supprimée.")
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de {table_name}: {e}")
            
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Réinitialisation de la base de données terminée.")

if __name__ == "__main__":
    reset_database()
