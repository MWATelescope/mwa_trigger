.. _grb-logic:

Gamma-ray Burst Triggering Logic
================================

The function used to process GRBs is :py:meth:`mwa_trigger.trigger_logic.worth_observing_grb`.
The following flow diagram explains how the inputs to this function are
used to decide to trigger, ignore or pending a human's decision.

.. mermaid::

   flowchart TD
      F[GRB] --> J{"(fermi_detection_prob > fermi_min_detection_prob \nand\n fermi_most_likely_index  4)\nor\nswift_rate_signif > swift_min_rate_signif"}
      J --> |True| K{"trig_min_duration < trig_duration < trig_max_duration"}
      J --> |False| END[Ignore]
      K --> |True| L[Trigger Observation]
      K --> |False| M{"pending_min_duration_1 < trig_duration < pending_max_duration_1\nor\npending_min_duration_2 < trig_duration < pending_max_duration_2"}
      M --> |True| N[Pending a human's decision]
      M --> |False| END
      style L fill:green,color:white
      style N fill:orange,color:white
      style END fill:red,color:white