

from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

import pymysql
import pandas as pd
from google.cloud import storage
import logging
import os

args = {
    'owner': 'Manish-Dhodare',
}

GCP_PROJECT_ID = 'nalen-430906'
EXPORT_URI = 'gs://{PROJECT_ID}-data-bucket/mysql_export/from_composer/stations/stations.csv'.format(
    PROJECT_ID=GCP_PROJECT_ID)
SQL_QUERY = "SELECT * FROM apps_db.stations"

# MySQL Connection Details (ASSUMPTIONS - PLEASE UPDATE THESE)
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_USER = os.environ.get("MYSQL_USER", "mysql_user")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "mysql_password")
MYSQL_DB = os.environ.get("MYSQL_DB", "apps_db")

def _export_mysql_to_gcs():
    """
    Connects to MySQL, extracts data, and uploads it to GCS.
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
        temp_csv_path = "/tmp/stations.csv"
        df.to_csv(temp_csv_path, index=False)
        logging.info(f"Data saved to temporary CSV: {temp_csv_path}")

        # Upload to GCS
        bucket_name = EXPORT_URI.split('/')[2]
        destination_blob_name = '/'.join(EXPORT_URI.split('/')[3:])
        
        storage_client = storage.Client(project=GCP_PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_filename(temp_csv_path)
        logging.info(f"File {temp_csv_path} uploaded to gs://{bucket_name}/{destination_blob_name}.")

        os.remove(temp_csv_path)
        logging.info(f"Temporary file {temp_csv_path} removed.")

    except Exception as e:
        logging.error(f"Error during MySQL to GCS export: {e}")
        raise

with DAG(
    dag_id='level_2_dag_load_bigquery',
    default_args=args,
    schedule='0 5 * * *',
    start_date=days_ago(1),
    catchup=False,
) as dag:
    export_mysql_to_gcs_task = PythonOperator(
        task_id='export_mysql_to_gcs_task',
        python_callable=_export_mysql_to_gcs,
    )

    gcs_to_bq_example = GCSToBigQueryOperator(
        task_id="gcs_to_bq_example",
        bucket='{}-data-bucket'.format(GCP_PROJECT_ID),
        source_objects=['mysql_export/from_composer/stations/stations.csv'],
        destination_project_dataset_table='raw_bikesharing.stations',
        schema_fields=[
            {'name': 'station_id', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'name', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'region_id', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'capacity', 'type': 'INTEGER', 'mode': 'NULLABLE'}
        ],
        write_disposition='WRITE_TRUNCATE'
    )

    bq_to_bq = BigQueryInsertJobOperator(
        task_id="bq_to_bq",
        configuration={
                "query": {
                    "query": "SELECT count(*) as count FROM `raw_bikesharing.stations`",
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

    export_mysql_to_gcs_task >> gcs_to_bq_example >> bq_to_bq

if __name__ == "__main__":
    dag.cli()