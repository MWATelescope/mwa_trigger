# Web App Installation
```
sudo apt-get install postgresql postgresql-contrib libpq-dev python3-dev graphviz
```

Set the envionment variables `DB_USER`, `DB_PASSWORD` and `DB_SECRET_KEY`


## Start the postgres database
```
sudo -u postgres psql

CREATE DATABASE trigger_db;
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD "$DB_PASSWORD";

ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET timezone TO 'UTC';
```

## Create a super user
```
python manage.py makemigrations
python manage.py migrate --run-syncdb
python manage.py createsuperuser
```

# Using the database

## Create a non admin
Use `BASE_URL/admin/auth/user/add/` To make a new user then if they would like alerts make them fill out `BASE_URL/user_alert_status/`

## Manually uploading a VOEvent
If you are only pushing static XML files for testing, you won't need the Twisted or Comet packages installed.

You can send a test trigger by doing something like:
```
cat trigger.xml | ./upload_xml.py
```


# Trigger Types Notes

## Fermi
Fermi docs: https://gcn.gsfc.nasa.gov/fermi.html

The Fermi spacecraft has two instruments (GBM and LAT). GBM triggers about 20 times per month while LAT only detects about 5 per year so we currently haven't bothered implimenting LAT triggers

```
                 TIME SINCE    LOCATION
TYPE             BURST         ACCURACY           COMMENTS
                               (radius)
=========        ============  ==========         ========
GBM_Alert        ~5sec         n/a                First GBM Notice, Timestamp Alert
GBM_Flt_Pos      ~10sec        15deg(1 sigma)     First (of a series) Position Notice, Flight-calculated
GBM_Gnd_Pos      20-300sec     1-10deg+3sys       Position Notice, Automated-Ground-calculated
GBM_Final_Pos    ~2 hr         1-3deg+3sys        Position Notice, Human-in-the-Loop-Ground-calculated

GBM_Subthresh    0.5-6 hr      10-40deg stat+sys  Below on-board trigger criteria, ground pipeline found
```
We only parse GBM_Flt_Pos, GBM_Gnd_Pos, GBM_Final_Pos because they have reasonable location accuracy.

## SWIFT
Swift docs: https://gcn.gsfc.nasa.gov/swift.html

We use SWIFT_BAT_GRB_Pos for the initial trigger and SWIFT_XRT_Pos to follow up or repoint.