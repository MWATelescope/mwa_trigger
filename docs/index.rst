.. tracet documentation master file, created by
   sphinx-quickstart on Wed Feb  2 15:46:42 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to TraceT's documentation!
=======================================

This documentation is split into three sections.
The Web Application documentation explains how to use the trigger web application.
The Trigger Logic documentation explains the logic we use to decide if we should
observe different sources and explain some of the telescope's VOEvent information.
The tracet documentation describes the python package and its functions that can be
used to parse XML files, decide if sources are worth observing and trigger observations
with the MWA and ATCA.

.. toctree::
   :maxdepth: 4
   :caption: Introduction:
   
   what_is_tracet
   overview_of_tracet

.. toctree::
   :maxdepth: 4
   :caption: Web Application:

   installation
   running_server
   new_proposal
   new_user
   using_the_database
   mwa_frequency_specifications


.. toctree::
   :maxdepth: 4
   :caption: Trigger Logic:

   voevent_handling
   grb
   event_telescopes


.. toctree::
   :maxdepth: 4
   :caption: TraceT Package:

   parse_xml_module
   trigger_logic_module
   triggerservice_module

.. toctree::
   :maxdepth: 4
   :caption: Further Reading:
   
   glossary