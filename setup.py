#! /usr/bin/env python
"""Setup for tracet
"""
from setuptools import setup


setup(name="tracet",
      version=0.1,
      description="VOEvent handling daemon and library for generating triggered MWA observations",
      url="https://github.com/ADACS-Australia/tracet.git",
      #long_description=read('README.md'),
      packages=['tracet'],
      package_data={'tracet':['data/*.txt',]},
      python_requires='>=3.6',
      install_requires=[
            'numpy',
            'pandas',
            'voevent-parse',
            # The below is only required with GW_LIGO.py which we will likely remove soon
            'healpy',
            'mwa_pb'
      ],
      scripts=['webapp_tracet/upload_xml.py'],
      setup_requires=['pytest-runner'],
      tests_require=['pytest']
)