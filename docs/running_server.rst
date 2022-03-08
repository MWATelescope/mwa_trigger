Running Server
==============

All commands assume you're in the trigger_webapp sub directory. You can see the output of the server with

.. code-block::

   tail -f uwsgi-emperor.log

Starting the server
-------------------

Start the uwsgi server with

.. code-block::

   uwsgi --ini trigger_webapp_uwsgi.ini

Restarting the server
---------------------

.. code-block::

   kill -HUP `cat /tmp/project-master.pid`

Stopping the server
-------------------

.. code-block::

   uwsgi --stop /tmp/project-master.pid
