Using the database
==================


Manually uploading a VOEvent
----------------------------
If you are only pushing static XML files for testing, you won't need the Twisted or Comet packages installed.

You can send a test trigger by doing something like:

.. code-block::

   cat trigger.xml | ./upload_xml.py
