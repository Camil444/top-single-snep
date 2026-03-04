import psycopg2
import os
import logging
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://db_user:db_password@localhost:5432/db")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

CREATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS labels (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS artists (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS producers (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS writers (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS songs (
    id             SERIAL PRIMARY KEY,
    titre          TEXT NOT NULL,
    main_artist_id INT REFERENCES artists(id),
    label_id       INT REFERENCES labels(id),
    release_date   DATE,
    sample_type    TEXT,
    sample_from    TEXT,
    UNIQUE (titre, main_artist_id)
);
CREATE TABLE IF NOT EXISTS song_artists (
    song_id   INT NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    artist_id INT NOT NULL REFERENCES artists(id),
    position  SMALLINT NOT NULL DEFAULT 1,
    PRIMARY KEY (song_id, artist_id)
);
CREATE TABLE IF NOT EXISTS song_producers (
    song_id     INT NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    producer_id INT NOT NULL REFERENCES producers(id),
    PRIMARY KEY (song_id, producer_id)
);
CREATE TABLE IF NOT EXISTS song_writers (
    song_id   INT NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    writer_id INT NOT NULL REFERENCES writers(id),
    PRIMARY KEY (song_id, writer_id)
);
CREATE TABLE IF NOT EXISTS chart_entries (
    id         SERIAL PRIMARY KEY,
    song_id    INT NOT NULL REFERENCES songs(id),
    annee      SMALLINT NOT NULL,
    semaine    SMALLINT NOT NULL,
    classement SMALLINT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (annee, semaine, classement)
);
CREATE INDEX IF NOT EXISTS idx_chart_annee_semaine ON chart_entries(annee, semaine);
CREATE INDEX IF NOT EXISTS idx_chart_classement    ON chart_entries(classement);
CREATE INDEX IF NOT EXISTS idx_chart_song_id       ON chart_entries(song_id);
CREATE INDEX IF NOT EXISTS idx_artists_name        ON artists(name);
CREATE INDEX IF NOT EXISTS idx_producers_name      ON producers(name);
CREATE INDEX IF NOT EXISTS idx_writers_name        ON writers(name);
CREATE INDEX IF NOT EXISTS idx_labels_name         ON labels(name);
CREATE INDEX IF NOT EXISTS idx_songs_main_artist   ON songs(main_artist_id);
"""


def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.error(f"DB connection error: {e}")
        raise


def create_schema():
    """Creates all tables if they do not exist (idempotent)."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(CREATE_SCHEMA_SQL)
        conn.commit()
        logger.info("Schema verified/created.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating schema: {e}")
    finally:
        cur.close()
        conn.close()


def _upsert_entity(cur, table, name):
    """Returns the id of the entity, inserting it if needed. Returns None for empty names."""
    if not name or str(name).strip() in ('', 'None', 'nan', 'NaT'):
        return None
    normalized = str(name).strip().upper()
    cur.execute(
        f"INSERT INTO {table} (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
        (normalized,)
    )
    return cur.fetchone()[0]


def _insert_single_row(conn, item):
    """Inserts one enriched scrape row into the normalized schema."""
    cur = conn.cursor()
    try:
        # Label
        label_id = None
        editeur = item.get('editeur')
        if editeur and str(editeur).strip() not in ('', 'None', 'nan'):
            cur.execute(
                "INSERT INTO labels (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
                (str(editeur).strip(),)
            )
            label_id = cur.fetchone()[0]

        # Main artist
        main_artist_id = _upsert_entity(cur, 'artists', item.get('artiste'))

        # Song
        titre = str(item.get('titre', '')).strip()
        if not titre:
            return

        release_date = item.get('release_date')
        if release_date and str(release_date).strip() in ('', 'None', 'nan', 'NaT'):
            release_date = None

        cur.execute(
            """
            INSERT INTO songs (titre, main_artist_id, label_id, release_date, sample_type, sample_from)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (titre, main_artist_id) DO UPDATE SET
                label_id     = COALESCE(EXCLUDED.label_id,     songs.label_id),
                release_date = COALESCE(EXCLUDED.release_date, songs.release_date),
                sample_type  = COALESCE(EXCLUDED.sample_type,  songs.sample_type),
                sample_from  = COALESCE(EXCLUDED.sample_from,  songs.sample_from)
            RETURNING id
            """,
            (titre, main_artist_id, label_id, release_date or None,
             item.get('sample_type') or None, item.get('sample_from') or None)
        )
        song_id = cur.fetchone()[0]

        # Artists (positions 1-4)
        for position, key in enumerate(['artiste', 'artiste_2', 'artiste_3', 'artiste_4'], start=1):
            artist_id = _upsert_entity(cur, 'artists', item.get(key))
            if artist_id:
                cur.execute(
                    "INSERT INTO song_artists (song_id, artist_id, position) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (song_id, artist_id, position)
                )

        # Producers
        for key in ['producer_1', 'producer_2']:
            producer_id = _upsert_entity(cur, 'producers', item.get(key))
            if producer_id:
                cur.execute(
                    "INSERT INTO song_producers (song_id, producer_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (song_id, producer_id)
                )

        # Writers
        for key in ['writer_1', 'writer_2']:
            writer_id = _upsert_entity(cur, 'writers', item.get(key))
            if writer_id:
                cur.execute(
                    "INSERT INTO song_writers (song_id, writer_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (song_id, writer_id)
                )

        # Chart entry
        cur.execute(
            """
            INSERT INTO chart_entries (song_id, annee, semaine, classement)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (annee, semaine, classement) DO NOTHING
            """,
            (song_id, item['annee'], item['semaine'], item['classement'])
        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting row (titre={item.get('titre')}, semaine={item.get('semaine')}): {e}")
    finally:
        cur.close()


def insert_record(data_list, year):
    """
    Inserts a list of enriched dicts into the normalized schema.
    Called by update.py after scraping + Genius enrichment.
    """
    create_schema()

    if not data_list:
        return

    conn = get_db_connection()
    try:
        for item in data_list:
            _insert_single_row(conn, item)
        logger.info(f"Processed {len(data_list)} records for year {year}.")
    finally:
        conn.close()


def load_csvs_to_db():
    """Loads all CSV files from data/ into the normalized database."""
    csv_files = sorted(DATA_DIR.glob("top_singles_*.csv"))

    if not csv_files:
        logger.warning("No CSV files found in data/")
        return

    create_schema()

    for csv_file in csv_files:
        try:
            year = int(csv_file.stem.split('_')[-1])
            logger.info(f"Loading {csv_file.name} (year {year})...")
            df = pd.read_csv(csv_file)
            df = df.where(pd.notnull(df), None)
            data_list = df.to_dict('records')

            conn = get_db_connection()
            try:
                for item in data_list:
                    _insert_single_row(conn, item)
                logger.info(f"  Loaded {len(data_list)} rows from {csv_file.name}")
            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Error loading {csv_file.name}: {e}")


def get_last_scraped_week(year):
    """Returns the last week present in chart_entries for a given year."""
    create_schema()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT MAX(semaine) FROM chart_entries WHERE annee = %s", (year,))
        result = cur.fetchone()
        return result[0] if result and result[0] is not None else 0
    except Exception as e:
        logger.error(f"Error getting last week for {year}: {e}")
        return 0
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    logger.info("Loading CSV files into normalized database...")
    load_csvs_to_db()
    logger.info("Done.")
