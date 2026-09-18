#!/bin/bash
sudo -u postgres psql -c "CREATE DATABASE ffmotors_db;"
sudo -u postgres psql -c "CREATE USER ffmotors_user WITH PASSWORD 'ffm_secure_2026';"
sudo -u postgres psql -c "ALTER ROLE ffmotors_user SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE ffmotors_user SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE ffmotors_user SET timezone TO 'Europe/London';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ffmotors_db TO ffmotors_user;"
sudo -u postgres psql -d ffmotors_db -c "GRANT ALL ON SCHEMA public TO ffmotors_user;"
