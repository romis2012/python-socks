#!/usr/bin/env python
import codecs
import os
import re
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = None

with codecs.open(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), 'python_socks', '_version.py'),
    'r',
    'latin1',
) as fp:
    try:
        version = re.findall(r"^__version__ = '([^']+)'\r?$", fp.read(), re.M)[0]
    except IndexError:
        raise RuntimeError('Unable to determine version.')

if sys.version_info < (3, 6, 1):
    raise RuntimeError('python-socks requires Python >= 3.6.2')

with open('README.md') as f:
    long_description = f.read()

setup(
    name='python-socks',
    author='Roman Snegirev',
    author_email='snegiryev@gmail.com',
    version=version,
    license='Apache 2',
    url='https://github.com/romis2012/python-socks',
    description='Core proxy (SOCKS4, SOCKS5, HTTP tunneling) functionality for Python',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=[
        'python_socks',
        'python_socks._proto',
        'python_socks._protocols',
        'python_socks._connectors',
        'python_socks.sync',
        'python_socks.sync.v2',
        'python_socks.async_',
        'python_socks.async_.asyncio',
        'python_socks.async_.asyncio.v2',
        'python_socks.async_.trio',
        'python_socks.async_.trio.v2',
        'python_socks.async_.curio',
        'python_socks.async_.anyio',
        'python_socks.async_.anyio.v2',
    ],
    keywords='socks socks5 socks4 http proxy asyncio trio curio anyio',
    extras_require={
        'asyncio': ['async-timeout>=3.0.1'],
        'trio': ['trio>=0.16.0'],
        'curio': ['curio>=1.4'],
        'anyio': ['anyio>=3.3.4'],
    },
)
