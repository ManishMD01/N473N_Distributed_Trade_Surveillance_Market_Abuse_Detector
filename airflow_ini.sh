 #!/bin/bash
#
# Description: This script automates the setup of an Apache Airflow environment.
#              It creates a Python virtual environment, installs Apache Airflow
#              with a specified version and constraints, and then initializes
#              Airflow in standalone mode.
#
# Usage: ./airflow_ini.sh
#
# Prerequisites:
#   - Python 3 installed
#   - pip (Python package installer)
#
# Author: Manish Dhodare
# Date: July 26, 2026
# Version: 1.0
#
python3 -m venv .venv
source .venv/bin/activate
AIRFLOW_VERSION=2.9.3

PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"

CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"


export AIRFLOW_HOME=~/airflow

airflow standalone

#End of the script. 