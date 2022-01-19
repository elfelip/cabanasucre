#!/usr/bin/env python3

from logging.config import valid_ident
import signal
import sys
import time
import RPi.GPIO as GPIO

class NiveauCtrlCmd:

    NIV_BAS_ALERTE = 4
    NIV_BAS = 17
    NIV_MAX = 27
    NIV_MAX_ALERTE = 22
    def __init__(self) -> None:
        GPIO.setmode(GPIO.BCM)
    
        connecteurs = [self.NIV_BAS_ALERTE, self.NIV_BAS, self.NIV_MAX, self.NIV_MAX_ALERTE]

        for connecteur in connecteurs:
            GPIO.setup(connecteur, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.add_event_detect(connecteur, GPIO.BOTH, callback=self.traiter_inputs_callback, bouncetime=200)
        self.DERNIER_NIVEAU = None
        self.traiter_inputs_callback(channel=None)

    def lancer_alerte_vide(self):
        print("Alerte, Le chaudron est vide.")

    def lancer_alerte_min(self):
        print("Le réservoir est au niveau minimum.")

    def lancer_alerte_normal(self):
        print("Le niveau du réservoir est normal pour le bouillage")
        
    def ouvrir_valve(self):
        print("Ouvrir la valve pour ajouter de l'eau.")
        
    def fermer_valve(self):
        print("Fermer le valve.")
        
    def lancer_alerte_niveau_haut(self):
        print("Le niveau du réservoir est haut.")

    def lancer_alerte_max(self):
        print("Alerte, le niveau maiximal est atteint, il y a probablement un problème avec la valve.")    

    def lancer_erreur_niveau(self):
        print("Les informations de niveau sont incohérents. Il doit y avoir un problème avec la sonde.")

    def traiter_inputs_callback(self, channel=None):
        if channel is not None:
            print("Channel: {0}".format(channel))
        time.sleep(0.5)
        if ((GPIO.input(self.NIV_MIN) and not 
            (GPIO.input(self.NIV_BAS) or GPIO.input(self.NIV_MAX) or GPIO.input(self.NIV_MAX_ALERTE)))):
            self.lancer_min()
            if self.DERNIER_NIVEAU is None or self.DERNIER_NIVEAU == "normal":
                self.ouvrir_valve()
            self.DERNIER_NIVEAU = "min"
        elif ((GPIO.input(self.NIV_BAS_ALERTE) and GPIO.input(self.NIV_BAS)) and not
            (GPIO.input(self.NIV_MAX) or GPIO.input(self.NIV_MAX_ALERTE))):
            self.lancer_alerte_normal()
            self.DERNIER_NIVEAU = "normal"
        elif ((GPIO.input(self.NIV_BAS_ALERTE) and GPIO.input(self.NIV_BAS) and GPIO.input(self.NIV_MAX)) and not
            GPIO.input(self.NIV_MAX_ALERTE)):
            self.lancer_alerte_haut()
            self.fermer_valve()
            self.DERNIER_NIVEAU = "haut"
        elif (GPIO.input(self.NIV_BAS_ALERTE) and GPIO.input(self.NIV_BAS) and GPIO.input(self.NIV_MAX)) and GPIO.input(self.NIV_MAX_ALERTE):
            self.fermer_valve()
            self.lancer_alerte_max()
            self.DERNIER_NIVEAU = "max_alerte"
        elif not (GPIO.input(self.NIV_BAS_ALERTE) or GPIO.input(self.NIV_BAS) or GPIO.input(self.NIV_MAX) or GPIO.input(self.NIV_MAX_ALERTE)):
            self.lancer_alerte_vide()
            self.ouvrir_valve()
            self.DERNIER_NIVEAU = "vide"
        else:
            self.fermer_valve()
            self.lancer_erreur_niveau()
            self.DERNIER_NIVEAU = "erreur"

def signal_handler(sig, frame):
        GPIO.cleanup()
        sys.exit(0)

def main():
    crtl_cmd = NiveauCtrlCmd()
    signal.signal(signal.SIGINT, crtl_cmd.signal_handler)
    signal.pause()

if __name__ == "__main__":
    main()