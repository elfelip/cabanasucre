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
    MIN = 1
    BAS = 2
    NORMAL = 3
    HAUT = 4
    MAX = 5
    
    def __init__(self):
        print("setmode: GPIO.BCM: {0}".format(GPIO.BCM))
        GPIO.setmode(GPIO.BCM)
    
        connecteurs = [self.NIV_MIN, self.NIV_BAS, self.NIV_HAUT, self.NIV_MAX]

        for connecteur in connecteurs:
            print ("setup connecteur {0} mode GPIO.IN: {1} pull_up_down GPIO.PUD_DOWN {3}".format(
                connecteur, 
                GPIO.IN,
                GPIO.PUD_DOWN))
            GPIO.setup(connecteur, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            rising_callback = None
            falling_callback = None
            if connecteur == self.NIV_MIN:
                rising_callback = self.traiter_gpio_rising_pour_sonde_min
                falling_callback = self.traiter_gpio_falling_pour_sonde_min
            if connecteur == self.NIV_BAS:
                rising_callback = self.traiter_gpio_rising_pour_sonde_bas
                falling_callback = self.traiter_gpio_falling_pour_sonde_bas
            if connecteur == self.NIV_HAUT:
                rising_callback = self.traiter_gpio_rising_pour_sonde_haut
                falling_callback = self.traiter_gpio_falling_pour_sonde_haut
            if connecteur == self.NIV_MAX:
                rising_callback = self.traiter_gpio_rising_pour_sonde_max
                falling_callback = self.traiter_gpio_falling_pour_sonde_max
            if rising_callback is not None and falling_callback is not None:
                print ("add_event_detect connecteur: {0}, GPIO.RISING {1}".format(connecteur, GPIO.RISING))
                GPIO.add_event_detect(connecteur, GPIO.RISING, callback=rising_callback, bouncetime=200)
                print ("add_event_detect connecteur: {0}, GPIO.FALLING {1}".format(connecteur, GPIO.FALLING))
                GPIO.add_event_detect(connecteur, GPIO.FALLING, callback=falling_callback, bouncetime=200)
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

    def traiter_gpio_rising_pour_sonde_min(self, channel=None):
        if self.NIVEAU != self.BAS:
            self.lancer_alerte_bas()
        self.NIVEAU = self.BAS
    
    def traiter_gpio_falling_pour_sonde_min(self, channel=None):
        if self.NIVEAU != self.MIN:
            self.ouvrir_valve()
            self.lancer_alerte_min()
        self.NIVEAU = self.MIN

    def traiter_gpio_rising_pour_sonde_bas(self, channel=None):
        if self.NIVEAU != self.NORMAL:
            self.lancer_alerte_normal()
        self.NIVEAU = self.NORMAL
    
    def traiter_gpio_falling_pour_sonde_bas(self, channel=None):
        if self.NIVEAU != self.BAS:
            self.ouvrir_valve()
            self.lancer_alerte_min()
        self.NIVEAU = self.BAS

    def traiter_gpio_rising_pour_sonde_haut(self, channel=None):
        if self.NIVEAU != self.HAUT:
            self.fermer_valve()
            self.lancer_alerte_haut()
        self.NIVEAU = self.HAUT
    
    def traiter_gpio_falling_pour_sonde_haut(self, channel=None):
        if self.NIVEAU != self.NORMAL:
            self.lancer_alerte_normal()
        self.NIVEAU = self.NORMAL

    def traiter_gpio_rising_pour_sonde_max(self, channel=None):
        if self.NIVEAU != self.MAX:
            self.fermer_valve()
            self.lancer_alerte_max()
        self.NIVEAU = self.MAX
    
    def traiter_gpio_falling_pour_sonde_max(self, channel=None):
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
            self.NIVEAU = self.MIN
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