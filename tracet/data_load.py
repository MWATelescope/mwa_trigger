"""
Loads all the data required by tracet from the data directory.
"""

import os

datadir = os.path.join(os.path.dirname(__file__), 'data')

# Hard code the path of the Maxi FlareStarNames file
MAXI_FLARE_STAR_NAMES = os.path.join(datadir, 'FlareStarNames.txt')
# Hard code the path of the Swift flare star catalogue file
SWIFT_FLARE_STAR_NAMES = os.path.join(datadir, 'onboardswiftcat_201704.txt')