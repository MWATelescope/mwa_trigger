"""
Loads all the data required by mwa_trigger from the data directory.
"""

import os

datadir = os.path.join(os.path.dirname(__file__), 'data')

# Hard code the path of the FlareStarNames file
FLARE_STAR_NAMES = os.path.join(datadir, 'FlareStarNames.txt')