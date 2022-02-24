.. _freq_spec:
Installation
============

For Ubuntu or Debian Linux:
.. code-block::

   sudo apt-get install postgresql postgresql-contrib libpq-dev python3-dev graphviz

Then install the python requirements (recommended in its own virtual environment) using:

.. code-block::

   pip install -r trigger_webapp/requirements.txt

Environment Variables
--------------------

To run the web application, you will need to set the following environment variables:

.. csv-table:: Envionment Variables
   :header: "Variable","Description"

   "DB_USER","Postgres user name which you will set in the next section."
   "DB_PASSWORD","Postgres password which you will set in the next section."
   "DB_SECRET_KEY", "Django secret key. `Here <https://saasitive.com/tutorial/generate-django-secret-key/>`_ is a description of how to generate one."
   "TWILIO_ACCOUNT_SID", "Your SID from your `Twilio Account <https://www.twilio.com/>`_ which will be billed for the SMS and calls the database generates."
   "TWILIO_AUTH_TOKEN", "Your auth token from your `Twilio Account <https://www.twilio.com/>`_ which will be billed for the SMS and calls the database generates."
   "GMAIL_APP_PASSWORD", "The app password for the mwa.trigger@gmail.com email. This can be supplied by Nick Swainston."
   "MWA_SECURE_KEY", "This a project dependent secure key to schedule MWA observations. Contact the MWA operations team to receive one."
   "ATCA_SECURE_KEY_FILE", "This a project dependent secure key file to schedule ATCA observations. Contact the ATCA operations team to receive one."

Start the Postgres Database
---------------------------

The following commands will set up the Postgres database for the web app. Replace $DB_USER and $DB_PASSWORD with the environment variable values.

.. code-block::

   sudo -u Postgres psql

   CREATE DATABASE trigger_db;
   CREATE USER $DB_USER WITH ENCRYPTED PASSWORD "$DB_PASSWORD";

   ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
   ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
   ALTER ROLE $DB_USER SET timezone TO 'UTC';


Create a superuser
-------------------

These commands will set up a superuser account.

.. code-block::

   python manage.py makemigrations
   python manage.py migrate --run-syncdb
   python manage.py createsuperuser