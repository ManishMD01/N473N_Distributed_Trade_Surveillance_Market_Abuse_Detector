
#
# DAG: MySQL to GCS to BigQuery Data Pipeline
# Description: This DAG extracts data from a MySQL database, loads it into BigQuery via GCS,
#              and then performs a simple count query as a data quality check.
# Author: Gemini
# Date: 2026-08-02
#

from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.providers.google.cloud.hooks.gcs import GCSHook

import pandas as pd
import logging

args = {
    'owner': 'Manish-Dhodare',
    'gcp_conn_id': 'google_cloud_default'
}

GCP_PROJECT_ID = 'nalen-430906'
GCS_BUCKET = 'gemini-de-bucket'  # UPDATE WITH YOUR GCS BUCKET
GCS_OBJECT_NAME = 'stations.csv'
BQ_DATASET = 'raw_bikesharing'
BQ_TABLE = 'stations'
SQL_QUERY = "SELECT * FROM apps_db.stations"

# It is recommended to use Airflow Connections to store credentials securely.
# Replace the following with a call to the MySQL connection defined in Airflow UI.
# For example: mysql_hook = MySqlHook(mysql_conn_id='your_mysql_conn_id')
MYSQL_CONN_ID = "mysql_default" 

def _export_mysql_to_gcs():
    """
    Connects to MySQL, extracts data, converts it to a CSV in-memory,
    and uploads it to a GCS bucket.
    """
    mysql_hook = MySqlHook(mysql_conn_id=MYSQL_CONN_ID)
    gcs_hook = GCSHook(gcp_conn_id=args['gcp_conn_id'])

    logging.info(f"Connecting to MySQL using connection '{MYSQL_CONN_ID}'")
    try:
        conn = mysql_hook.get_conn()
        logging.info("MySQL connection successful.")

        df = pd.read_sql(SQL_QUERY, conn)
        conn.close()
        logging.info(f"Successfully extracted {len(df)} rows from MySQL.")

        # Convert DataFrame to CSV in-memory
        csv_data = df.to_csv(index=False)
        logging.info("Data converted to CSV in-memory.")

        # Upload to GCS from memory
        logging.info(f"Uploading in-memory CSV to GCS bucket {GCS_BUCKET} as {GCS_OBJECT_NAME}")
        gcs_hook.upload(
            bucket_name=GCS_BUCKET,
            object_name=GCS_OBJECT_NAME,
            data=csv_data,
            mime_type='text/csv',
        )
        logging.info("Upload to GCS successful.")

    except Exception as e:
        logging.error(f"Error during MySQL to GCS export: {e}")
        raise

with DAG(
    dag_id='level_2_dag_gcs_to_bigquery_load',
    default_args=args,
    schedule='0 5 * * *',
    start_date=days_ago(1),
    catchup=False,
    tags=['gcs', 'bigquery'],
) as dag:
    export_mysql_to_gcs_task = PythonOperator(
        task_id='export_mysql_to_gcs_task',
        python_callable=_export_mysql_to_gcs,
    )

    load_gcs_to_bq_task = GCSToBigQueryOperator(
        task_id='load_gcs_to_bq_task',
        bucket=GCS_BUCKET,
        source_objects=[GCS_OBJECT_NAME],
        destination_project_dataset_table=f'{GCP_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}',
        schema_fields=[
            {'name': 'station_id', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'name', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'region_id', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'capacity', 'type': 'INTEGER', 'mode': 'NULLABLE'},
        ],
        write_disposition='WRITE_TRUNCATE',
        source_format='CSV',
        skip_leading_rows=1,
    )

    bq_data_quality_check = BigQueryInsertJobOperator(
        task_id="bq_data_quality_check",
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
        },
        gcp_conn_id=args['gcp_conn_id'],
    )

    export_mysql_to_gcs_task >> load_gcs_to_bq_task >> bq_data_quality_check