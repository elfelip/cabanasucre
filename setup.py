#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
from setuptools import setup

setup(
    # Needed to silence warnings (and to be a worthwhile package)
    name='bouillage_ctrl_cmd',
    url='https://github.com/elfelip/cabanasucre.git',
    author='Philippe Gauthier',
    author_email='elfelip@yahoo.com',
    # Needed to actually package something
    packages=['bouillage_ctrl_cmd','bouillage_controle'],
    # Needed for dependencies
    install_requires=[],
    # *strongly* suggested for sharing
    version='0.0.1',
    #version_command=('git describe', "pep440-git-local"),
    # The license can be anything you like
    license='',
    description='Controle de la production sirop erable',
    long_description=io.open('README.md', 'r', encoding="utf-8").read(),
)

