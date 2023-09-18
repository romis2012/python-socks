#!/usr/bin/env python
import os
import re
import sys

from setuptools import setup


if sys.version_info < (3, 6, 1):
    raise RuntimeError('python-socks requires Python >= 3.6.2')


def get_version():
    here = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(here, 'python_socks', '_version.py')
    contents = open(filename).read()
    pattern = r"^__version__ = '(.*?)'$"
    return re.search(pattern, contents, re.MULTILINE).group(1)


def get_long_description():
    with open('README.md', mode='r', encoding='utf8') as f:
        return f.read()


setup(
    name='python-socks',
    author='Roman Snegirev',
    author_email='snegiryev@gmail.com',
    version=get_version(),
    license='Apache 2',
    url='https://github.com/romis2012/python-socks',
    description='Core proxy (SOCKS4, SOCKS5, HTTP tunneling) functionality for Python',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    packages=[
        'python_socks',
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
        'anyio': ['anyio>=3.3.4,<5.0.0'],
    },
)
