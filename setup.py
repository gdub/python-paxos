from distutils.core import setup


setup(
    name='paxos',
    version='0.1',
    author='Gary Wilson Jr. and Michael Stathopoulos',
#    author_email='',
    packages=['paxos'],
    url='https://github.com/gdub/python-paxos',
    license='MIT',
    description='A demo implementation of the Paxos algorithm implemented in Python.',
    long_description=open('README.rst').read(),
)
