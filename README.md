# SNEP Top 50 Analytics & Dashboard

A full-stack data project that scrapes weekly French music charts (SNEP), enriches data via Genius API, stores it in PostgreSQL, and visualizes trends in a modern Next.js dashboard.

## 🏗 Architecture

- **ETL Pipeline**: Python scripts scrape SNEP website and fetch metadata from Genius (Producers, Writers, Samples).
- **Orchestration**: Apache Airflow schedules weekly updates.
- **Database**: PostgreSQL stores historical chart data (2020-Present).
- **Frontend**: Next.js (React) + Tailwind CSS + Recharts for interactive analytics.
- **Infrastructure**: Fully containerized with Docker Compose.

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- Genius API Access Token
- `requirements.txt` (optional, for local development without Docker)

### Installation

1.  **Clone the repository**

    ```bash
    git clone <repo-url>
    cd top_50_snep
    ```

2.  **Start the stack**

    ```bash
    docker-compose up -d
    ```

3.  **Access Services**
    - **Dashboard**: [http://localhost:3000](http://localhost:3000)
    - **Airflow**: [http://localhost:8080](http://localhost:8080) (User/Pass: `admin`/`admin` - _check logs if different_)

### Manual Data Update (Airflow)

1.  Go to Airflow UI.
2.  Trigger the `snep_update_weekly` DAG.
3.  The pipeline will scrape missing weeks and update the DB.

## 📂 Project Structure

- `airflow/`: DAGs and Airflow configuration.
- `scripts/`: Python ETL scripts (`scrap.py`, `update_data.py`, `insert_record.py`).
- `viz_dashboard/`: Next.js frontend application.
- `postgres/`: Database initialization and data storage.
- `data/`: CSV backups of chart data.

---

_Built with Python, Next.js, Docker._
