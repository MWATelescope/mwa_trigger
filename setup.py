from setuptools import setup

setup(
  name='mwa_trigger',
  version='1.0.0',
  packages=['mwa_trigger'],
  package_data={'mwa_trigger':['python_requirements.txt', 'trigger.conf.example']},
  url='git@github.com:MWATelescope/mwa_trigger',
  license='GPLv3',
  author='Andrew Williams, Paul Hancock, Gemma Anderson',
  author_email='Andrew.Williams@curtin.edu.au',
  description='Code to parse VOEvents and generate triggered MWA observations',
  scripts=['push_voevent.py', 'pyro_nameserver.py', 'voevent_handler.py'],
  install_requires=["numpy", "astropy", 'Pyro4', 'Twisted', 'Comet']
)
