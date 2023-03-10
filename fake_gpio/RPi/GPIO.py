#!/usr/bin/env python3
# -*- coding: utf-8 -*-

BCM = 1
IN = 2
OUT = 3
BOTH = 4
PUD_DOWN = 5
RISING = 6
FALLING = 7
HIGH = 1
LOW = 0
RPI_REVISION = 1

def setmode(mode):
    pass

def setup(connecteur, mode, pull_up_down, initial):
    pass

def add_event_detect(connecteur, mode, callback, bouncetime):
    pass

def input(connecteur):
    return False

def output(connecteur, niveau):
    pass