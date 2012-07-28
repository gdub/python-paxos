from setuptools import setup, find_packages


CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.2',
    'Topic :: Communications',
    'Topic :: Scientific/Engineering',
    'Topic :: System :: Clustering',
]


setup(
    name='paxos',
    version='0.1',
    classifiers=CLASSIFIERS,
    author='Gary Wilson Jr. and Michael Stathopoulos',
#    author_email='',
    packages=find_packages(),
    url='https://github.com/gdub/python-paxos',
    license='MIT',
    description='A demo implementation of the Paxos algorithm implemented in Python.',
    long_description=open('README.rst').read(),
)
