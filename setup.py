#! /usr/bin/env python
"""Setup for mwa_trigger
"""
from setuptools import setup


setup(name="mwa_trigger",
      version=0.1,
      description="VOEvent handling daemon and library for generating triggered MWA observations",
      url="https://github.com/ADACS-Australia/mwa_trigger.git",
      #long_description=read('README.md'),
      packages=['mwa_trigger'],
      package_data={'mwa_trigger':['data/*.txt',]},
      python_requires='>=3.6',
      install_requires=[
            'numpy',
            'pandas',
            'voevent-parse',
            # The below is only required with GW_LIGO.py which we will likely remove soon
            'healpy',
            'mwa_pb'
      ],
      scripts=['trigger_webapp/upload_xml.py'],
      setup_requires=['pytest-runner'],
      tests_require=['pytest']
)