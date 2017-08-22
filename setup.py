'''A basic API wrapper for interacting with the SmarterMail API service

See:
https://github.com/jhannah01/smapi
'''

import os.path
import codecs
import pkg_resources
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

try:
    with codecs.open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
        long_description = f.read()
except:
    long_description = None

from smapi import __version__ as smapi_version

setup(
    name='smapi',
    version=smapi_version,
    description='A basic API wrapper for interacting with SmarterMail',
    long_description=long_description,
    url='https://github.com/jhannah01/smapi',
    license='GNU',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries',
        'Topic :: Communications :: Email'
    ],
    keywords='smartermail smapi smartertools',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=[
        'requests',
        'beautifulsoup4',
        'simplejson'
    ],
    entry_points={
        'console_scripts': ['smapi=smapi.cli:run_clitool']
    }
)

