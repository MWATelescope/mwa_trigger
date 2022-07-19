TraceT
======

TraceT is the web-app for the Transient RApid-response using Coordinated Event Triggering (TRACE-T) project which is led by Gemma Anderson.
The web-app evolved out of two previous automated transient triggering projects, one on the Murchison Widefield Array (`MWA <https://www.mwatelescope.org/>`_), and one on the Australia Telescope Compact Array (`ATCA <https://www.narrabri.atnf.csiro.au/>`_).
The MWA triggering project is described in `Hancock et al, 2019 <https://ui.adsabs.harvard.edu/abs/2019PASA...36...46H/abstract>`_ and `Anderson et al, 2021 <https://ui.adsabs.harvard.edu/abs/2021PASA...38...26A/abstract>`_.

The two pieces of triggering software monitor streams of `Virtual Observatory <https://ivoa.net/>`_ events (`VOevents <https://voevent.readthedocs.io/en/latest/>`_)
looking for messages from satellites such as `Swift <https://swift.gsfc.nasa.gov/>`_ and `Fermi <https://fermi.gsfc.nasa.gov/>`_ 
and triggering follow up observations using the MWA or ATCA.

These two initial triggering pipelines were able to trigger observations, however it was not easy for project members to know the status of the software, what the current triggering conditions were, or whether a VOEvent had generated an observation.
To combat these difficulties Astronomy Data And Computing Services (`ADACS <https://adacs.org.au/>`_) was brought in to develop a single web app that would provide a single point of reference for multiple triggering programs on both the MWA and ATCA, whilst also giving the project members a user interface to easily monitor the current state of the system.