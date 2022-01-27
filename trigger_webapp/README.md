## Install requirements

sudo apt-get install postgresql postgresql-contrib libpq-dev python3-dev

Set the envionment variables DB_USER, DB_PASSWORD, DB_SECRET_KEY


## Start the postgres database
sudo -u postgres psql

CREATE DATABASE trigger_db;
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD "$DB_PASSWORD";

ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET timezone TO 'UTC';

## Create a super user
python manage.py makemigrations
python manage.py migrate --run-syncdb
python manage.py createsuperuser


## Create a non admin
Use

BASE_URL/admin/auth/user/add/

To make a new user then if they would like alerts make them fill out

BASE_URL/user_alert_status/
