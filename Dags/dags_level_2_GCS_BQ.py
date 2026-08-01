

from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.models.param import Param

import pymysql
import pandas as pd
from google.cloud import bigquery
import logging
import os

args = {
    'owner': 'Manish-Dhodare',
}

GCP_PROJECT_ID = 'nalen-430906'
BQ_DATASET = 'raw_bikesharing'
BQ_TABLE = 'stations'
SQL_QUERY = "SELECT * FROM apps_db.stations"
TEMP_CSV_PATH = "/tmp/stations.csv"

# MySQL Connection Details (ASSUMPTIONS - PLEASE UPDATE THESE)
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_USER = os.environ.get("MYSQL_USER", "mysql_user")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "mysql_password")
MYSQL_DB = os.environ.get("MYSQL_DB", "apps_db")

def _export_mysql_to_local_csv():
    """
    Connects to MySQL, extracts data, and saves it to a local CSV file.
    """
    logging.info(f"Connecting to MySQL at {MYSQL_HOST}:{MYSQL_PORT} with user {MYSQL_USER}, database {MYSQL_DB}")
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            db=MYSQL_DB
        )
        logging.info("MySQL connection successful.")

        df = pd.read_sql(SQL_QUERY, conn)
        conn.close()
        logging.info(f"Successfully extracted {len(df)} rows from MySQL.")

        # Save to a temporary CSV file
        df.to_csv(TEMP_CSV_PATH, index=False)
        logging.info(f"Data saved to temporary CSV: {TEMP_CSV_PATH}")
        return TEMP_CSV_PATH
    except Exception as e:
        logging.error(f"Error during MySQL to local CSV export: {e}")
        raise

def _load_local_csv_to_bq(**context):
    """
    Loads data from a local CSV file to BigQuery.
    """
    file_path = context['ti'].xcom_pull(task_ids='export_mysql_to_local_csv_task')
    if not file_path or not os.path.exists(file_path):
        raise ValueError(f"File path not found or does not exist: {file_path}")

    logging.info(f"Loading data from {file_path} to BigQuery table {GCP_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}")
    try:
        client = bigquery.Client(project=GCP_PROJECT_ID)
        table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"

        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("station_id", "STRING"),
                bigquery.SchemaField("name", "STRING"),
                bigquery.SchemaField("region_id", "STRING"),
                bigquery.SchemaField("capacity", "INTEGER"),
            ],
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=False,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )

        with open(file_path, "rb") as source_file:
            job = client.load_table_from_file(source_file, table_id, job_config=job_config)

        job.result()  # Wait for the job to complete
        logging.info(f"Loaded {job.output_rows} rows into {table_id}.")
    
    except Exception as e:
        logging.error(f"Error loading data from local CSV to BigQuery: {e}")
        raise
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"Temporary file {file_path} removed.")

with DAG(
    dag_id='level_2_dag_load_bigquery',
    default_args=args,
    schedule='0 5 * * *',
    start_date=days_ago(1),
    catchup=False,
) as dag:
    export_mysql_to_local_csv_task = PythonOperator(
        task_id='export_mysql_to_local_csv_task',
        python_callable=_export_mysql_to_local_csv,
    )

    load_local_csv_to_bq_task = PythonOperator(
        task_id='load_local_csv_to_bq_task',
        python_callable=_load_local_csv_to_bq,
    )

    bq_to_bq = BigQueryInsertJobOperator(
        task_id="bq_to_bq",
        configuration={
                "query": {
                    "query": f"SELECT count(*) as count FROM `{GCP_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}`",
                    "useLegacySql": False,
                    "destinationTable": {
                        "projectId": GCP_PROJECT_ID,
                        "datasetId": "dwh_bikesharing",
                        "tableId": "temporary_stations_count"
                    },
                    "createDisposition": 'CREATE_IF_NEEDED',
                    "writeDisposition": 'WRITE_TRUNCATE',
                    "priority": "BATCH",
                }
        }
    )

    export_mysql_to_local_csv_task >> load_local_csv_to_bq_task >> bq_to_bq

if __name__ == "__main__":
    dag.cli()