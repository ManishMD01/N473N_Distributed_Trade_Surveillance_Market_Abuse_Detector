-- Manual setup (run as a PostgreSQL superuser via psql)
-- Usage:
--   psql -h localhost -U postgres -v db_name=surveillance -v db_user=surveillance -v db_password="'surveillance'" -f scripts/setup_timescaledb.sql
-- Then apply schema:
--   psql -h localhost -U postgres -d surveillance -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"  (if available)
--   psql -h localhost -U surveillance -d surveillance -f db/schema.sql

\set ON_ERROR_STOP on
\if :{?db_name}
\else
\set db_name surveillance
\endif
\if :{?db_user}
\else
\set db_user surveillance
\endif
-- db_password must be a SQL literal including quotes, e.g. -v db_password="'secret'"

SELECT format('CREATE ROLE %I LOGIN PASSWORD %s', :'db_user', :db_password)
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'db_user')\gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'db_name', :'db_user')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'db_name')\gexec

SELECT format('GRANT ALL PRIVILEGES ON DATABASE %I TO %I', :'db_name', :'db_user')\gexec
