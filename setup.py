#! /usr/bin/env python
"""Setup for mwa_trigger
"""
from setuptools import setup


reqs = ['numpy',
        'voevent-parse',
       ]


setup(name="mwa_trigger",
      version=0.1,
      description="VOEvent handling daemon and library for generating triggered MWA observations",
      url="https://github.com/ADACS-Australia/mwa_trigger.git",
      #long_description=read('README.md'),
      packages=['mwa_trigger'],
      #package_data={},
      python_requires='>=3.6',
      install_requires=reqs,
      scripts=[],
      setup_requires=['pytest-runner'],
      tests_require=['pytest']
)