#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from logging.config import valid_ident
import signal
import sys
import time
import RPi.GPIO as GPIO

class NiveauCtrlCmd:

    NIV_MIN_R = 5
    NIV_MIN_F = 12
    NIV_BAS_R = 17
    NIV_BAS_F = 16
    NIV_HAUT_R = 27
    NIV_HAUT_F = 24
    NIV_MAX_R = 22
    NIV_MAX_F = 25
    ERREUR = 0
    MIN = 1
    BAS = 2
    NORMAL = 3
    HAUT = 4
    MAX = 5
    
    
    
    def __init__(self):
        self.connecteurs = [
            {
                "numero": self.NIV_MIN_R,
                "nom": "NIV_MIN_R",
                "mode": GPIO.IN,
                "detect": GPIO.RISING,
                "callback": self.traiter_gpio_rising_pour_sonde_min
            },
            {
                "numero": self.NIV_MIN_F,
                "nom": "NIV_MIN_F",
                "mode": GPIO.IN,
                "detect": GPIO.FALLING,
                "callback": self.traiter_gpio_falling_pour_sonde_min
            },
            {
                "numero": self.NIV_BAS_R,
                "nom": "NIV_BAS_R",
                "mode": GPIO.IN,
                "detect": GPIO.RISING,
                "callback": self.traiter_gpio_rising_pour_sonde_bas
            },
            {
                "numero": self.NIV_BAS_F,
                "nom": "NIV_BAS_F",
                "mode": GPIO.IN,
                "detect": GPIO.FALLING,
                "callback": self.traiter_gpio_falling_pour_sonde_bas
            },
            {
                "numero": self.NIV_HAUT_R,
                "nom": "NIV_HAUT_R",
                "mode": GPIO.IN,
                "detect": GPIO.RISING,
                "callback": self.traiter_gpio_rising_pour_sonde_haut
            },
            {
                "numero": self.NIV_HAUT_F,
                "nom": "NIV_HAUT_F",
                "mode": GPIO.IN,
                "detect": GPIO.FALLING,
                "callback": self.traiter_gpio_falling_pour_sonde_haut
            },
            {
                "numero": self.NIV_MAX_R,
                "nom": "NIV_MAX_R",
                "mode": GPIO.IN,
                "detect": GPIO.RISING,
                "callback": self.traiter_gpio_rising_pour_sonde_max
            },
            {
                "numero": self.NIV_MAX_F,
                "nom": "NIV_MAX_F",
                "mode": GPIO.IN,
                "detect": GPIO.FALLING,
                "callback": self.traiter_gpio_falling_pour_sonde_max
            },
            
        ]
        print("setmode: GPIO.BCM: {0}".format(GPIO.BCM))
        GPIO.setmode(GPIO.BCM)

        for connecteur in self.connecteurs:
            print ("setup connecteur {0} mode GPIO.IN: {1} pull_up_down GPIO.PUD_DOWN {2}".format(
                connecteur["numero"], 
                connecteur["mode"],
                GPIO.PUD_DOWN))
            GPIO.setup(connecteur["numero"], connecteur["mode"], pull_up_down=GPIO.PUD_DOWN)
            if connecteur["callback"] is not None:
                print ("add_event_detect connecteur: {0}, detect {1}, callback : {2}".format(
                    connecteur["numero"], 
                    connecteur["detect"],
                    connecteur["callback"]))
                GPIO.add_event_detect(connecteur["numero"], connecteur["detect"], callback=connecteur["callback"], bouncetime=200)
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
        if ((GPIO.input(self.NIV_MIN_R) and not 
            (GPIO.input(self.NIV_BAS_R) or GPIO.input(self.NIV_HAUT_R) or GPIO.input(self.NIV_MAX_R)))):
            self.NIVEAU = self.BAS
        elif ((GPIO.input(self.NIV_MIN_R) and GPIO.input(self.NIV_BAS_R)) and not
            (GPIO.input(self.NIV_HAUT_R) or GPIO.input(self.NIV_MAX_R))):
            self.NIVEAU = self.NORMAL
        elif ((GPIO.input(self.NIV_MIN_R) and GPIO.input(self.NIV_BAS_R) and GPIO.input(self.NIV_HAUT_R)) and not
            GPIO.input(self.NIV_MAX_R)):
            self.NIVEAU = self.HAUT
        elif ((GPIO.input(self.NIV_MIN_R) and GPIO.input(self.NIV_BAS_R) and
                GPIO.input(self.NIV_HAUT_R)) and GPIO.input(self.NIV_MAX_R)):
            self.NIVEAU = self.MAX
        elif not (GPIO.input(self.NIV_MIN_R) or GPIO.input(self.NIV_BAS_R)
                or GPIO.input(self.NIV_HAUT_R) or GPIO.input(self.NIV_MAX_R)):
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