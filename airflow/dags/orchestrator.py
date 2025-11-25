from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os

default_args = {
    'owner': 'airflow',
    'description': 'Orchestrator for scraping and inserting SNEP data and Genius API',
    'start_date': datetime(2025, 11, 23),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

with DAG(
    dag_id='snep_update_weekly',
    default_args=default_args,
    schedule_interval='0 11 * * *', # Every day at 11:00 AM
    catchup=False
) as dag:

    update_task = BashOperator(
        task_id='run_update_script',
        bash_command='cd /opt/airflow/project/scripts && python update.py',
        env={
            'TARGET_YEAR': '2025',
            'DB_HOST': os.getenv('DB_HOST', 'db'),
            'GENIUS_ACCESS_TOKEN': os.getenv('GENIUS_ACCESS_TOKEN')
        }
    )

    update_task
