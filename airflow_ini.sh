 #!/bin/bash
python3 -m venv .venv
source .venv/bin/activate
AIRFLOW_VERSION=2.9.3

PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"

CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"



#inside airflow-env

export AIRFLOW_HOME=~/airflow

airflow standalone
