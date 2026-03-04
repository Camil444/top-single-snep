#!/usr/bin/env python3
"""
Migration script: Migrates from the old flat schema (top_singles_YYYY)
to the new normalized schema.

New schema:
  labels, artists, producers, writers
  songs (titre, main_artist_id, label_id, release_date, sample_type, sample_from)
  song_artists (song_id, artist_id, position)
  song_producers (song_id, producer_id)
  song_writers (song_id, writer_id)
  chart_entries (song_id, annee, semaine, classement)
"""

import psycopg2
from psycopg2 import sql
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://db_user:db_password@localhost:5432/db")

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
    return psycopg2.connect(DATABASE_URL)


def create_schema(conn):
    cur = conn.cursor()
    cur.execute(CREATE_SCHEMA_SQL)
    conn.commit()
    cur.close()
    logger.info("New schema created successfully.")


def _upsert_entity(cur, table, name):
    """Inserts entity if not exists, returns its id. Returns None if name is empty."""
    if not name or str(name).strip() in ('', 'None', 'nan'):
        return None
    normalized = str(name).strip().upper()
    cur.execute(
        f"INSERT INTO {table} (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
        (normalized,)
    )
    return cur.fetchone()[0]


def insert_normalized_row(conn, data):
    """Inserts a single row from the old flat schema into the new normalized schema."""
    cur = conn.cursor()
    try:
        # 1. Label
        label_id = None
        editeur = data.get('editeur')
        if editeur and str(editeur).strip() not in ('', 'None', 'nan'):
            cur.execute(
                "INSERT INTO labels (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
                (str(editeur).strip(),)
            )
            label_id = cur.fetchone()[0]

        # 2. Main artist
        main_artist_id = _upsert_entity(cur, 'artists', data.get('artiste'))

        # 3. Song (titre + main_artist_id = unique key)
        titre = str(data.get('titre', '')).strip()
        if not titre:
            conn.rollback()
            return

        release_date = data.get('release_date')
        if release_date and str(release_date).strip() in ('', 'None', 'nan', 'NaT'):
            release_date = None

        sample_type = data.get('sample_type') or None
        sample_from = data.get('sample_from') or None

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
            (titre, main_artist_id, label_id, release_date, sample_type, sample_from)
        )
        song_id = cur.fetchone()[0]

        # 4. Song artists (up to 4)
        for position, key in enumerate(['artiste', 'artiste_2', 'artiste_3', 'artiste_4'], start=1):
            artist_id = _upsert_entity(cur, 'artists', data.get(key))
            if artist_id:
                cur.execute(
                    "INSERT INTO song_artists (song_id, artist_id, position) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (song_id, artist_id, position)
                )

        # 5. Producers
        for key in ['producer_1', 'producer_2']:
            producer_id = _upsert_entity(cur, 'producers', data.get(key))
            if producer_id:
                cur.execute(
                    "INSERT INTO song_producers (song_id, producer_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (song_id, producer_id)
                )

        # 6. Writers
        for key in ['writer_1', 'writer_2']:
            writer_id = _upsert_entity(cur, 'writers', data.get(key))
            if writer_id:
                cur.execute(
                    "INSERT INTO song_writers (song_id, writer_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (song_id, writer_id)
                )

        # 7. Chart entry
        cur.execute(
            """
            INSERT INTO chart_entries (song_id, annee, semaine, classement)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (annee, semaine, classement) DO NOTHING
            """,
            (song_id, data['annee'], data['semaine'], data['classement'])
        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error migrating row (titre={data.get('titre')}, annee={data.get('annee')}, semaine={data.get('semaine')}): {e}")
    finally:
        cur.close()


def migrate_data(conn):
    """Migrates all data from the old flat tables into the new normalized schema."""
    years = range(2020, 2027)
    total_migrated = 0

    for year in years:
        table_name = f"top_singles_{year}"
        check_cur = conn.cursor()
        check_cur.execute("SELECT to_regclass(%s)", (table_name,))
        exists = check_cur.fetchone()[0]
        check_cur.close()

        if not exists:
            logger.info(f"Table {table_name} does not exist, skipping.")
            continue

        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]
        cur.close()

        logger.info(f"Migrating {len(rows)} rows from {table_name}...")
        for row in rows:
            insert_normalized_row(conn, dict(zip(col_names, row)))

        total_migrated += len(rows)
        logger.info(f"  Done: {table_name}")

    logger.info(f"Migration complete. Total rows processed: {total_migrated}")


if __name__ == "__main__":
    logger.info("Starting schema migration...")
    conn = get_db_connection()
    try:
        create_schema(conn)
        migrate_data(conn)
        logger.info("Migration finished successfully.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()
