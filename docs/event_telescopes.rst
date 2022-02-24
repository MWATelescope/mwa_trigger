Event Telescope Notes
=====================

The following VOEvent telescope event types can be parsed and put throught our triggering logic

.. csv-table:: Event Telescope Pairs
   :header: "Telescope Names","Event Type"

   "SWIFT", "BAT_GRB_Pos"
   "SWIFT", "XRT_Pos"
   "Fermi", "GBM_Flt_Pos"
   "Fermi", "GBM_Gnd_Pos"
   "Fermi", "GBM_Fin_Pos"

If an Event telescope or type isn't in this list then you will need to update :py:meth:`mwa_trigger.parse_xml.parsed_VOEvent`


Fermi
-----

Fermi docs: https://gcn.gsfc.nasa.gov/fermi.html

The Fermi spacecraft has two instruments (GBM and LAT). GBM triggers about 20 times per month while LAT only detects about 5 per year so we currently haven't bothered implimenting LAT triggers

.. code-block::

                  TIME SINCE    LOCATION
   TYPE             BURST         ACCURACY           COMMENTS
                                 (radius)
   =========        ============  ==========         ========
   GBM_Alert        ~5sec         n/a                First GBM Notice, Timestamp Alert
   GBM_Flt_Pos      ~10sec        15deg(1 sigma)     First (of a series) Position Notice, Flight-calculated
   GBM_Gnd_Pos      20-300sec     1-10deg+3sys       Position Notice, Automated-Ground-calculated
   GBM_Final_Pos    ~2 hr         1-3deg+3sys        Position Notice, Human-in-the-Loop-Ground-calculated

   GBM_Subthresh    0.5-6 hr      10-40deg stat+sys  Below on-board trigger criteria, ground pipeline found

We only parse GBM_Flt_Pos, GBM_Gnd_Pos, GBM_Final_Pos because they have reasonable location accuracy.


SWIFT
-----

Swift docs: https://gcn.gsfc.nasa.gov/swift.html

We use SWIFT_BAT_GRB_Pos for the initial trigger and SWIFT_XRT_Pos to follow up or repoint.
