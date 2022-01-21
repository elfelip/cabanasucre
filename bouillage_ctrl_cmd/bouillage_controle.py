#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from logging.config import valid_ident
import signal
import sys
import time
import RPi.GPIO as GPIO

class NiveauCtrlCmd:

    NIV_MIN = 4
    NIV_BAS = 17
    NIV_HAUT = 27
    NIV_MAX = 22
    ERREUR = 0
    VIDE = 1
    MIN = 2
    BAS = 3
    NORMAL = 4
    HAUT = 5
    MAX = 6
    
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
    
        connecteurs = [self.NIV_MIN, self.NIV_BAS, self.NIV_HAUT, self.NIV_MAX]

        for connecteur in connecteurs:
            GPIO.setup(connecteur, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            up_callback = None
            down_callback = None
            if connecteur == self.NIV_MIN:
                up_callback = self.traiter_gpio_up_pour_sonde_min
                down_callback = self.traiter_gpio_down_pour_sonde_min
            if connecteur == self.NIV_BAS:
                up_callback = self.traiter_gpio_up_pour_sonde_bas
                down_callback = self.traiter_gpio_down_pour_sonde_bas
            if connecteur == self.NIV_HAUT:
                up_callback = self.traiter_gpio_up_pour_sonde_haut
                down_callback = self.traiter_gpio_down_pour_sonde_haut
            if connecteur == self.NIV_MAX:
                up_callback = self.traiter_gpio_up_pour_sonde_max
                down_callback = self.traiter_gpio_down_pour_sonde_max
            if up_callback is not None and down_callback is not None:
                GPIO.add_event_detect(connecteur, GPIO.UP, callback=up_callback, bouncetime=200)
                GPIO.add_event_detect(connecteur, GPIO.DOWN, callback=down_callback, bouncetime=200)
        self.mesurer_niveau()

    def lancer_alerte_vide(self):
        print("Alerte, Le chaudron est vide.")

    def lancer_alerte_min(self):
        print("Le reservoir est au niveau minimum.")

    def lancer_alerte_bas(self):
        print("Le reservoir est bas.")
        
    def lancer_alerte_normal(self):
        print("Le niveau du reservoir est normal pour le bouillage")
        
    def ouvrir_valve(self):
        print("Ouvrir la valve pour ajouter de l'eau.")
        
    def fermer_valve(self):
        print("Fermer le valve.")
        
    def lancer_alerte_haut(self):
        print("Le niveau du reservoir est haut.")

    def lancer_alerte_max(self):
        print("Alerte, le niveau maiximal est atteint, il y a probablement un probleme avec la valve.")    

    def lancer_erreur_niveau(self):
        print("Les informations de niveau sont incoherents. Il doit y avoir un probleme avec la sonde.")

    def traiter_gpio_up_pour_sonde_min(self, channel=None):
        if self.NIVEAU != self.BAS:
            self.lancer_alerte_bas()
        self.NIVEAU = self.BAS
    
    def traiter_gpio_down_pour_sonde_min(self, channel=None):
        if self.NIVEAU != self.MIN:
            self.lancer_alerte_min()
        self.NIVEAU = self.MIN

    def traiter_gpio_up_pour_sonde_bas(self, channel=None):
        if self.NIVEAU != self.NORMAL:
            self.lancer_alerte_normal()
        self.NIVEAU = self.NORMAL
    
    def traiter_gpio_down_pour_sonde_bas(self, channel=None):
        if self.NIVEAU != self.BAS:
            self.ouvrir_valve()
            self.lancer_alerte_min()
        self.NIVEAU = self.BAS

    def traiter_gpio_up_pour_sonde_haut(self, channel=None):
        if self.NIVEAU != self.HAUT:
            self.fermer_valve()
            self.lancer_alerte_haut()
        self.NIVEAU = self.HAUT
    
    def traiter_gpio_down_pour_sonde_haut(self, channel=None):
        if self.NIVEAU != self.NORMAL:
            self.lancer_alerte_normal()
        self.NIVEAU = self.NORMAL

    def traiter_gpio_up_pour_sonde_max(self, channel=None):
        if self.NIVEAU != self.MAX:
            self.fermer_valve()
            self.lancer_alerte_max()
        self.NIVEAU = self.MAX
    
    def traiter_gpio_down_pour_sonde_max(self, channel=None):
        if self.NIVEAU != self.HAUT:
            self.lancer_alerte_haut()
        self.NIVEAU = self.HAUT

    def mesurer_niveau(self):
        if ((GPIO.input(self.NIV_MIN) and not 
            (GPIO.input(self.NIV_BAS) or GPIO.input(self.NIV_HAUT) or GPIO.input(self.NIV_MAX)))):
            self.NIVEAU = self.BAS
        elif ((GPIO.input(self.NIV_MIN) and GPIO.input(self.NIV_BAS)) and not
            (GPIO.input(self.NIV_HAUT) or GPIO.input(self.NIV_MAX))):
            self.NIVEAU = self.NORMAL
        elif ((GPIO.input(self.NIV_MIN) and GPIO.input(self.NIV_BAS) and GPIO.input(self.NIV_HAUT)) and not
            GPIO.input(self.NIV_MAX)):
            self.NIVEAU = self.HAUT
        elif (GPIO.input(self.NIV_MIN) and GPIO.input(self.NIV_BAS) and GPIO.input(self.NIV_HAUT)) and GPIO.input(self.NIV_MAX):
            self.NIVEAU = self.MAX
        elif not (GPIO.input(self.NIV_MIN) or GPIO.input(self.NIV_BAS) or GPIO.input(self.NIV_HAUT) or GPIO.input(self.NIV_MAX)):
            self.NIVEAU = self.VIDE
        else:
            self.NIVEAU = self.ERREUR

def signal_handler(sig, frame):
        GPIO.cleanup()
        sys.exit(0)

def main():
    crtl_cmd = NiveauCtrlCmd()
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

if __name__ == "__main__":
    main()