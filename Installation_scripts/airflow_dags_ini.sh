#!/bin/bash
#
# Script: airflow_dags_ini.sh
# Description: This script activates the Airflow environment and performs DAG operations (list, reserialize).
# Author: Gemini CLI Agent
# Date: 2026-08-01

cd ~/airflow-env

# Activate the environment

source .venv/bin/activate

# Now try the command again

airflow dags list

airflow dags reserialize

airflow dags list