#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
from setuptools import setup

setup(
    # Needed to silence warnings (and to be a worthwhile package)
    name='RPi',
    url='https://github.com/elfelip/cabanasucre.git',
    author='Philippe Gauthier',
    author_email='elfelip@yahoo.com',
    # Needed to actually package something
    packages=['RPi'],
    # Needed for dependencies
    install_requires=[],
    # *strongly* suggested for sharing
    version='0.0.3',
    #version_command=('git describe', "pep440-git-local"),
    # The license can be anything you like
    license='',
    description='Librairies fake GPIO Raspberry PI pour tests',
    long_description=io.open('README.md', 'r', encoding="utf-8").read(),
)

