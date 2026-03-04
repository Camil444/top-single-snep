# SNEP Top 50 — Project Context for Claude

## Project Goal

Full-stack data project that **scrapes weekly French music charts (SNEP Top Singles)**, enriches them with metadata from the **Genius API**, stores the data in **PostgreSQL**, and visualizes trends in a **Next.js dashboard**.

Live demo: http://172.233.243.159:3000

---

## Tech Stack

| Layer          | Technology                          |
| -------------- | ----------------------------------- |
| Scraping       | Python (requests, BeautifulSoup)    |
| Enrichment     | Genius API (lyricsgenius)           |
| Database       | PostgreSQL 17 (via Docker)          |
| Orchestration  | Apache Airflow (Docker)             |
| Frontend       | Next.js 16 + React 19 + Tailwind 4  |
| Charts         | Recharts (via page.tsx components)  |
| Infrastructure | Docker Compose                      |

---

## Key Files & Directories

```
top_50_snep/
├── scripts/
│   ├── scrap.py          # SNEP scraper (BeautifulSoup), scrapes Top 200 per week
│   ├── update_data.py    # Genius API enrichment (producers, writers, samples, release_date)
│   ├── insert_record.py  # Inserts enriched data into normalized PostgreSQL schema
│   ├── update.py         # Orchestrates: scrape → enrich → insert for a given year/week
│   ├── reset_db.py       # Drops all tables (use before full_reload)
│   ├── migrate_schema.py # One-time migration from old flat schema to new normalized schema
│   └── full_reload.sh    # Full reload: reset + scrape all years 2020–present
├── data/
│   └── top_singles_YYYY.csv   # CSV backups per year (source of truth for cold reload)
├── airflow/
│   └── dags/orchestrator.py   # DAG: snep_update_weekly (daily at 11:00)
├── viz_dashboard/
│   ├── app/
│   │   ├── page.tsx              # Main dashboard UI (single page app)
│   │   └── api/
│   │       ├── stats/route.ts         # Rankings: artists / producers / editeurs
│   │       ├── artist-details/route.ts # Song details for a given entity
│   │       ├── search/route.ts         # Autocomplete search
│   │       ├── genres/route.ts         # Genre distribution
│   │       └── artist-image/route.ts   # Genius artist image proxy
│   └── lib/db.ts              # pg Pool connection (localhost:5432, db "db")
├── postgres/
│   └── airflow_init.sql       # Creates airflow DB user at Docker init
├── docker-compose.yaml        # Services: db (postgres), af (airflow)
├── database_diagram.md        # Full schema documentation
└── CLAUDE.md                  # This file
```

---

## Database Schema (Normalized — current)

9 tables. See `database_diagram.md` for full ERD and rationale.

**Core tables:**
- `artists`, `producers`, `writers`, `labels` — deduplicated entity tables (name stored UPPER, UNIQUE)
- `songs` — one row per unique song (titre + main_artist_id), metadata stored once
- `song_artists`, `song_producers`, `song_writers` — junction tables
- `chart_entries` — one row per weekly chart position (annee, semaine, classement)

**Key: no more per-year tables, no more UNION ALL in API queries, no more fixed artiste_1..4 columns.**

---

## DB Connection

- Host: `localhost` (or `db` inside Docker)
- Port: `5432`
- Database: `db`
- User: `db_user` / Password: `db_password`
- Airflow DB: `airflow_db`, user `airflow` / `airflow_password`

---

## Environment Variables

```env
POSTGRES_USER=db_user
POSTGRES_PASSWORD=db_password
POSTGRES_DB=db
DB_HOST=db               # inside Docker; use localhost for scripts run outside
GENIUS_ACCESS_TOKEN=...  # required for Genius enrichment
```

Loaded from `viz_dashboard/.env.local` (preferred) or root `.env`.

---

## Running the Project

### Start infrastructure
```bash
docker-compose up -d
```

### Full data reload (from CSV backups)
```bash
cd scripts
python insert_record.py   # loads all data/ CSVs into normalized schema
```

### Incremental update (new weeks)
```bash
cd scripts
python update.py          # scrape + enrich + insert missing weeks for current year
```

### Reset database
```bash
cd scripts
python reset_db.py        # drops all tables
```

### Run dashboard locally
```bash
cd viz_dashboard
npm run dev               # http://localhost:3000
```

---

## Data Flow

```
SNEP website → scrap.py → update_data.py (Genius) → insert_record.py → PostgreSQL
                                                                              ↓
                                                                   Next.js Dashboard
```

Airflow DAG `snep_update_weekly` runs `update.py` daily at 11:00 (inside Docker).

---

## Important Notes

- **Never use `rm -rf`** — use `trash` instead (macOS policy)
- CSV files in `data/` are kept as backups; `insert_record.py` can reload from them
- `song_cache_v2.json` is gitignored (large Genius API cache)
- Artist/producer names are normalized to UPPERCASE on insert
- The `songs` table uses `UNIQUE(titre, main_artist_id)` — same title by same artist = one row
- `chart_entries` uses `UNIQUE(annee, semaine, classement)` — only one song per position per week
