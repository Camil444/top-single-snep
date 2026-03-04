import psycopg2
from psycopg2 import sql
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://db_user:db_password@localhost:5432/db")


def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.error(f"DB connection error: {e}")
        raise


def reset_database():
    conn = get_db_connection()
    cur = conn.cursor()

    # Drop in reverse dependency order
    tables = [
        'chart_entries',
        'song_artists',
        'song_producers',
        'song_writers',
        'songs',
        'labels',
        'artists',
        'producers',
        'writers',
        # Old flat tables (kept for backward compat during transition)
        'top_singles_2020', 'top_singles_2021', 'top_singles_2022',
        'top_singles_2023', 'top_singles_2024', 'top_singles_2025', 'top_singles_2026',
    ]

    for table in tables:
        try:
            cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(table)))
            logger.info(f"Table {table} dropped.")
        except Exception as e:
            logger.error(f"Error dropping {table}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database reset complete.")


if __name__ == "__main__":
    reset_database()
