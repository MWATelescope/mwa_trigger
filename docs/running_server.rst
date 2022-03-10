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
