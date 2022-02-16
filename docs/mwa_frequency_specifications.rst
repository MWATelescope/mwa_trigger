.. _freq_spec:
MWA Frequency Specifications
============================

The MWA has a very flexible signal path that allows various frequency settings to suit your science.
The MWA has 24 coarse frequency channels that each have a bandwidth of 1.28Mhz and can
be arranged anywhere between 80 and 300 MHz. Each frequency channel ID has a centre
frequency of 1.28xID MHz. For example, channel ID 100 has a centre frequency of 128 MHz.
The frequency channels don't have to be contiguous, so we have a flexible "freqspec" how
you wish to arrange the frequency channels

Each freqspec is can be described as either:

.. code-block::

   <channel>
   <center>,<width>,<increment>
   <start>:<stop>:<increment>


where the increments default to 1.  Multiple entries can be given separated by a `;`


Example 1
---------
You want to observe with 24 contiguous frequency channels, centered on channel 121 (155 MHz):

.. code-block::

   121,24

Example 2
---------
24 channels, with gaps of 2 channels in between each, centered on 121:


.. code-block::

   121,24,3

which is the equivalent to:


.. code-block::

   109;112;115;118;121;124;127;130;131;132;133;134;135;136;137;138;139;140;141;142;143;144;145;146

Example 3
---------

Channels 101-112 inclusive, and channels 141-152 inclusive:

.. code-block::

   101:112;141:152

Example 4
---------
You want to list of 24 channels to use:

.. code-block::

   91;93;95;97;99;101;103;105;107;109;111;113;115;117;119;121;123;125;127;129;131;133;135;137
