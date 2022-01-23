#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from logging.config import valid_ident
import signal
import sys
import time
from tkinter import N
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
                "callback": self.traiter_event_detect_pour_sonde_niveau
            },
            {
                "numero": self.NIV_MIN_F,
                "nom": "NIV_MIN_F",
                "mode": GPIO.IN,
                "detect": GPIO.FALLING,
                "callback": self.traiter_event_detect_pour_sonde_niveau
            },
            {
                "numero": self.NIV_BAS_R,
                "nom": "NIV_BAS_R",
                "mode": GPIO.IN,
                "detect": GPIO.RISING,
                "callback": self.traiter_event_detect_pour_sonde_niveau
            },
            {
                "numero": self.NIV_BAS_F,
                "nom": "NIV_BAS_F",
                "mode": GPIO.IN,
                "detect": GPIO.FALLING,
                "callback": self.traiter_event_detect_pour_sonde_niveau
            },
            {
                "numero": self.NIV_HAUT_R,
                "nom": "NIV_HAUT_R",
                "mode": GPIO.IN,
                "detect": GPIO.RISING,
                "callback": self.traiter_event_detect_pour_sonde_niveau
            },
            {
                "numero": self.NIV_HAUT_F,
                "nom": "NIV_HAUT_F",
                "mode": GPIO.IN,
                "detect": GPIO.FALLING,
                "callback": self.traiter_event_detect_pour_sonde_niveau
            },
            {
                "numero": self.NIV_MAX_R,
                "nom": "NIV_MAX_R",
                "mode": GPIO.IN,
                "detect": GPIO.RISING,
                "callback": self.traiter_event_detect_pour_sonde_niveau
            },
            {
                "numero": self.NIV_MAX_F,
                "nom": "NIV_MAX_F",
                "mode": GPIO.IN,
                "detect": GPIO.FALLING,
                "callback": self.traiter_event_detect_pour_sonde_niveau
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
        self.NIVEAU = self.mesurer_niveau()
        self.afficher_niveau()

    def afficher_niveau(self, niveau=None):
        if niveau is None:
            niveau = self.NIVEAU
        if niveau == self.MIN:
            print ("Le niveau est sous le niveau minimum.")
        elif niveau == self.BAS:
            print ("Le niveau est bas.")
        elif niveau == self.HAUT:
            print ("Le niveau est haut.")
        elif niveau == self.MAX:
            print ("Le niveau est au dessus du niveau maximum.")
        else:
            print ("Le niveau est inconnu, verifier le systeme.")
            
    def alerter_changement_niveau(self, niveau=None):
        if niveau is None:
            niveau = self.NIVEAU
        if niveau == self.MIN:
            self.lancer_alerte_min()
        elif niveau == self.BAS:
            self.lancer_alerte_bas()
        elif niveau == self.HAUT:
            self.lancer_alerte_haut()
        elif niveau == self.MAX:
            self.lancer_alerte_max()
        else:
            self.lancer_erreur_niveau()

    def lancer_alerte_vide(self):
        print("Alerte, Le chaudron est vide.")

    def lancer_alerte_min(self):
        print("Alerte, Le reservoir est au niveau minimum.")

    def lancer_alerte_bas(self):
        print("Alerte, Le reservoir est bas.")
        
    def lancer_alerte_normal(self):
        print("Alerte, Le niveau du reservoir est normal pour le bouillage")
        
    def ouvrir_valve(self):
        print("Ouvrir la valve pour ajouter de l'eau.")
        
    def fermer_valve(self):
        print("Fermer le valve.")
        
    def lancer_alerte_haut(self):
        print("Le niveau du reservoir est haut.")

    def lancer_alerte_max(self):
        print("Alerte, le niveau maiximal est atteint, il y a probablement un probleme avec la valve.")    

    def lancer_erreur_niveau(self):
        print("Alerte Les informations de niveau sont incoherents. Il doit y avoir un probleme avec la sonde.")

    def traiter_event_detect_pour_sonde_niveau(self, channel=None):
        
        nouveau_niveau = self.mesurer_niveau()
        #if nouveau_niveau == self.ERREUR:
        #    tentatives = 0
        #    while nouveau_niveau == self.ERREUR and tentatives < 5:
        #        tentatives += 1
        #        time.sleep(0.5)
        #        nouveau_niveau = self.mesurer_niveau()
            
        if nouveau_niveau != self.NIVEAU and nouveau_niveau != self.ERREUR:
            if nouveau_niveau < self.NIVEAU and nouveau_niveau <= self.BAS:
                self.ouvrir_valve()
            elif nouveau_niveau > self.NIVEAU and nouveau_niveau >= self.HAUT:
                self.fermer_valve()
            self.afficher_niveau(niveau=nouveau_niveau)
            self.alerter_changement_niveau(niveau=nouveau_niveau)
        #elif nouveau_niveau == self.ERREUR:
        #    self.alerter_changement_niveau()
        self.NIVEAU = nouveau_niveau
            

    def mesurer_niveau(self):
        etat_niv_min = GPIO.input(self.NIV_MIN_R)
        etat_niv_bas = GPIO.input(self.NIV_BAS_F)
        etat_niv_haut = GPIO.input(self.NIV_HAUT_R)
        etat_niv_max = GPIO.input(self.NIV_MAX_R)
        print("NIV_MIN: {0}".format(etat_niv_min))
        print("NIV_BAS: {0}".format(etat_niv_bas))
        print("NIV_HAUT: {0}".format(etat_niv_haut))
        print("NIV_MAX: {0}".format(etat_niv_max))
        if ((etat_niv_min and not 
            (etat_niv_bas or etat_niv_haut or etat_niv_max))):
            return self.BAS
        elif ((etat_niv_min and etat_niv_bas) and not
            (etat_niv_haut or etat_niv_max)):
            return self.NORMAL
        elif ((etat_niv_min and etat_niv_bas and etat_niv_haut) and not
            etat_niv_max):
            return self.HAUT
        elif ((etat_niv_min and etat_niv_bas and
                etat_niv_haut) and etat_niv_max):
            return self.MAX
        elif not (etat_niv_min or etat_niv_bas
                or etat_niv_haut or etat_niv_max):
            return self.MIN
        else:
            return self.ERREUR

def signal_handler(sig, frame):
        GPIO.cleanup()
        sys.exit(0)

def main():
    crtl_cmd = NiveauCtrlCmd()
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

if __name__ == "__main__":
    main()