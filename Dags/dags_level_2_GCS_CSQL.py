from airflow.providers.google.cloud.operators.cloud_sql import CloudSQLExportInstanceOperator


sql_export_task = CloudSQLExportInstanceOperator(
        task_id='sql_export_task'
        project_id=nalen-430906,
        body=export_body,
        instance=INSTANCE_NAME
    )

    EXPORT_URI = 'gs://[your GCS bucket]/mysql_export/from_composer/stations/stations.csv'
SQL_QUERY = "SELECT * FROM DEWAW.stations"
export_body = {
    "exportContext": {
        "fileType": "csv",
        "uri": EXPORT_URI,
        "csvExportOptions":{
            "selectQuery": SQL_QUERY
        }
    }
}