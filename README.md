# SNEP Top 50 Analytics & Dashboard

**Live Demo:** [https://french-top-charts-analytics.vercel.app](https://french-top-charts-analytics.vercel.app)

![Dashboard Preview](artiste_picture/dashboard_example.png)

A full-stack data project that scrapes weekly French music charts (SNEP), enriches data via Genius API, stores it in PostgreSQL, and visualizes trends in a modern Next.js dashboard.

## Architecture

- **ETL Pipeline**: Python scripts scrape SNEP and fetch metadata from Genius (Producers, Writers, release dates).
- **Database**: PostgreSQL on [Neon](https://neon.tech) — normalized schema, 9 tables, 60k+ chart entries (2020–present).
- **Orchestration**: GitHub Actions — weekly cron job to update chart data automatically.
- **Frontend**: Next.js (React) + Tailwind CSS + Recharts, deployed on Vercel.

## Features

- **Multi-Year Analysis**: Browse Top 50 charts from 2020 to present.
- **Artist & Producer Analytics**: Visualize rankings, weeks in Top 50, and streaks.
- **Editor Analytics**: Track performance of music publishers/labels.
- **Smart Search**: Instantly find Artists, Producers, or Editors.
- **Data Enrichment**: Fetches producers, writers, and release dates via Genius API.

## Project Structure

- `scripts/`: Python ETL scripts (`update.py`, `insert_record.py`, `full_reload.sh`, etc.)
- `viz_dashboard/`: Next.js frontend application.
- `data/`: CSV backups of chart data.
- `airflow/`: Local Airflow DAGs (local dev/testing only).

## Local Development

### Prerequisites

- Python 3.9+
- Node.js 18+
- Docker (optional, for local PostgreSQL)

### Setup

1. **Clone the repository**

    ```bash
    git clone https://github.com/Camil444/top-single-snep.git
    cd top-single-snep
    ```

2. **Configure environment variables**

    ```bash
    # Root .env (for Python scripts)
    DATABASE_URL=postgresql://user:password@host:5432/db
    GENIUS_ACCESS_TOKEN=your_genius_token

    # viz_dashboard/.env.local (for Next.js)
    DATABASE_URL=postgresql://user:password@host:5432/db
    GENIUS_ACCESS_TOKEN=your_genius_token
    ```

3. **Run the dashboard**

    ```bash
    cd viz_dashboard
    npm install
    npm run dev
    ```

4. **Update chart data manually**

    ```bash
    python scripts/update.py
    ```

---

_Built with Python, Next.js, PostgreSQL (Neon), Vercel._
