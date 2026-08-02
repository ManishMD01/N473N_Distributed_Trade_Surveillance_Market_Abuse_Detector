
#!/bin/bash
#
# Script: Mysql_ini.sh
# Description: This script automates the installation and basic initialization of MySQL server.
# Author: Gemini CLI Agent
# Date: 2026-08-01

sudo apt-get update
sudo apt-get install mysql-server
sudo /etc/init.d/mysql start

sudo mysql

SELECT @@hostname;
