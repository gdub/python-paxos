from setuptools import setup, find_packages


setup(
    name='paxos',
    version='0.1',
    author='Gary Wilson Jr. and Michael Stathopoulos',
#    author_email='',
    packages=find_packages(),
    url='https://github.com/gdub/python-paxos',
    license='MIT',
    description='A demo implementation of the Paxos algorithm implemented in Python.',
    long_description=open('README.rst').read(),
)
