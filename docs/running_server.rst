Running Server
==============

Checking for errors and inspecting logs
---------------------------------------
nginx errors are in

.. code-block::

   tail -f cat /var/log/nginx/error.log

All commands assume you're in the webapp_tracet sub directory. You can see the output of the server with

.. code-block::

   tail -f uwsgi-emperor.log

.. _start_server:

Starting the server
-------------------

Start the uwsgi server with

.. code-block::

   uwsgi --ini webapp_tracet_uwsgi.ini

This will run in the background and the following sections describe how to restarting and stopping the server.

You also need to run the a twistd wrapper to listen for VOEvents. This can be run in tmux session using the command:

.. code-block::

   tmux new -s twistd_comet_wrapper

This will land you in the tmux session where you can run the wrapper command:

.. code-block::

   python twistd_comet_wrapper.py

This will start listening to VOEvents and you should see that "VOEvent Receiving Status" on the homepage changes from stopped to running.

You can detatch from the session with command `CTRL+B, D` and reattach with

.. code-block::

   tmux attach -t twistd_comet_wrapper


Restarting the server
---------------------

.. code-block::

   kill -HUP `cat /tmp/project-master.pid`


Stopping the server
-------------------

.. code-block::

   uwsgi --stop /tmp/project-master.pid


Installing updates
------------------

If the updates are small normally something as simple as the following will suffice:

.. code-block::

   git pull
   kill -HUP `cat /tmp/project-master.pid`

Larger updates may need a combination of the following commands

.. code-block::

   git pull
   # Stop server
   uwsgi --stop /tmp/project-master.pid
   # Check for new dependent software
   pip install -r requirements.txt
   # install updates to the tracet python module
   pip install ..
   # Check for new static files
   python manage.py collectstatic
   # Make any required changes to the backend database
   python manage.py makemigrations
   python manage.py migrate
   # Start server
   uwsgi --ini gleam_webapp_uwsgi.ini
