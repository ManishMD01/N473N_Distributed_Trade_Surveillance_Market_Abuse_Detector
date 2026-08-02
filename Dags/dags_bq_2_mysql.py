#
# DAG: BigQuery to MySQL Data Pipeline
# Description: This DAG exports data from a BigQuery table to a CSV file in GCS,
#              downloads the file, and then loads it into a MySQL database.
# Author: Gemini
# Date: 2026-08-02
#

from airflow import DAG
from airflow.providers.google.cloud.transfers.bigquery_to_gcs import BigQueryToGCSOperator
from airflow.providers.google.cloud.transfers.gcs_to_local import GCSToLocalFilesystemOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from airflow.providers.mysql.hooks.mysql import MySqlHook

import pandas as pd
import logging

# --- CONFIGURATION ---
# PLEASE UPDATE THESE VALUES FOR YOUR ENVIRONMENT
GCP_PROJECT_ID = 'nalen-430906'
GCS_BUCKET = 'gemini-de-bucket'
GCS_OBJECT_PATH = 'exports/stations_from_bq.csv'
LOCAL_FILE_PATH = f'/tmp/{GCS_OBJECT_PATH.split("/")[-1]}'

BQ_DATASET = 'raw_bikesharing'
BQ_TABLE = 'stations'

MYSQL_CONN_ID = "mysql_default"
MYSQL_TABLE = 'stations_from_bq' # This table will be created if it does not exist

# --- DAG ARGUMENTS ---
args = {
    'owner': 'Manish-Dhodare',
    'gcp_conn_id': 'google_cloud_default'
}

# --- PYTHON CALLABLE FOR LOADING DATA TO MYSQL ---
def _load_local_csv_to_mysql():
    """
    Reads a CSV file from the local filesystem and loads it into a MySQL table.
    """
    logging.info(f"Connecting to MySQL using connection '{MYSQL_CONN_ID}'")
    mysql_hook = MySqlHook(mysql_conn_id=MYSQL_CONN_ID)
    
    try:
        logging.info(f"Reading data from local CSV: {LOCAL_FILE_PATH}")
        df = pd.read_csv(LOCAL_FILE_PATH)
        logging.info(f"Successfully read {len(df)} rows from CSV.")

        logging.info(f"Loading data into MySQL table: {MYSQL_TABLE}")
        # Using pandas.to_sql for efficient bulk loading
        # The connection engine is created from the Airflow hook
        engine = mysql_hook.get_sqlalchemy_engine()
        df.to_sql(MYSQL_TABLE, con=engine, if_exists='replace', index=False)
        logging.info("Load to MySQL successful.")

    except Exception as e:
        logging.error(f"Error during CSV to MySQL load: {e}")
        raise

# --- DAG DEFINITION ---
with DAG(
    dag_id='bq_to_mysql_data_pipeline',
    default_args=args,
    schedule_interval='@daily',
    start_date=days_ago(1),
    catchup=False,
    tags=['bigquery', 'gcs', 'mysql'],
) as dag:

    export_bq_to_gcs = BigQueryToGCSOperator(
        task_id='export_bq_to_gcs',
        source_project_dataset_table=f'{GCP_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}',
        destination_cloud_storage_uris=[f'gs://{GCS_BUCKET}/{GCS_OBJECT_PATH}'],
        export_format='CSV',
        field_delimiter=',',
        print_header=True,
    )

    download_gcs_to_local = GCSToLocalFilesystemOperator(
        task_id='download_gcs_to_local',
        bucket=GCS_BUCKET,
        object_name=GCS_OBJECT_PATH,
        filename=LOCAL_FILE_PATH,
    )

    load_csv_to_mysql = PythonOperator(
        task_id='load_csv_to_mysql',
        python_callable=_load_local_csv_to_mysql,
    )

    cleanup_local_file = BashOperator(
        task_id='cleanup_local_file',
        bash_command=f'rm {LOCAL_FILE_PATH}',
    )

    # --- TASK DEPENDENCIES ---
    export_bq_to_gcs >> download_gcs_to_local >> load_csv_to_mysql >> cleanup_local_file
