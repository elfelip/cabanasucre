#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import glob
import signal
import sys
from time import localtime, strftime, sleep
import RPi.GPIO as GPIO
import logging
import threading
import os
from inspqcommun.kafka.producteur import obtenirConfigurationsProducteurDepuisVariablesEnvironnement, creerProducteur, publierMessage

class NiveauCtrlCmd:

    NIV_MIN_R = 5
    NIV_MIN_F = 12
    NIV_BAS_R = 17
    NIV_BAS_F = 23
    NIV_HAUT_R = 27
    NIV_HAUT_F = 24
    NIV_MAX_R = 22
    NIV_MAX_F = 25
    FERMER_VALVE = 16
    OUVRIR_VALVE = 26
    ERREUR = 0
    MIN = 1
    BAS = 2
    NORMAL = 3
    HAUT = 4
    MAX = 5
    NIVEAU = 0
    temps_signal_valve = 0.03
    topic_niveau = "bouillage.niveau"
    topic_alerte = "bouillage.alertes"
    topic_temp = "bouillage.temperature"
    producteur = None
    
    def __init__(self):
        self.valve_en_action = False
        self.valve_ouverte = False
        self.connecteurs = [
            {
                "numero": self.NIV_MIN_R,
                "nom": "NIV_MIN_R",
                "mode": GPIO.IN,
                "detect": GPIO.RISING,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_MIN_F,
                "nom": "NIV_MIN_F",
                "mode": GPIO.IN,
                "detect": GPIO.FALLING,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_BAS_R,
                "nom": "NIV_BAS_R",
                "mode": GPIO.IN,
                "detect": GPIO.RISING,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_BAS_F,
                "nom": "NIV_BAS_F",
                "mode": GPIO.IN,
                "detect": GPIO.FALLING,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_HAUT_R,
                "nom": "NIV_HAUT_R",
                "mode": GPIO.IN,
                "detect": GPIO.RISING,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_HAUT_F,
                "nom": "NIV_HAUT_F",
                "mode": GPIO.IN,
                "detect": GPIO.FALLING,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_MAX_R,
                "nom": "NIV_MAX_R",
                "mode": GPIO.IN,
                "detect": GPIO.RISING,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_MAX_F,
                "nom": "NIV_MAX_F",
                "mode": GPIO.IN,
                "detect": GPIO.FALLING,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.OUVRIR_VALVE,
                "nom": "OUVRIR_VALVE",
                "mode": GPIO.OUT,
                "initial": GPIO.LOW
            },
            {
                "numero": self.FERMER_VALVE,
                "nom": "FERMER_VALVE",
                "mode": GPIO.OUT,
                "initial": GPIO.LOW
            }
        ]
        logging.info("setmode: GPIO.BCM: {0}".format(GPIO.BCM))
        GPIO.setmode(GPIO.BCM)

        for connecteur in self.connecteurs:
            logging.info ("setup connecteur {0} mode: {1}".format(
                connecteur["numero"], 
                connecteur["mode"]))
            if connecteur["mode"] == GPIO.IN:
                pull_up_down = connecteur["pull_up_down"] if "pull_up_down" in connecteur else GPIO.PUD_DOWN
                GPIO.setup(connecteur["numero"], connecteur["mode"], pull_up_down=pull_up_down)
            elif connecteur["mode"] == GPIO.OUT:
                initial = connecteur["initial"] if "initial" in connecteur else GPIO.LOW
                GPIO.setup(connecteur["numero"], connecteur["mode"], initial=initial)

        for connecteur in self.connecteurs:
            if connecteur["mode"] == GPIO.IN:
                if "callback" in connecteur and "detect" in connecteur:
                    logging.info ("add_event_detect connecteur: {0}, detect {1}, callback : {2}".format(
                        connecteur["numero"], 
                        connecteur["detect"],
                        connecteur["callback"]))
                    GPIO.add_event_detect(connecteur["numero"], connecteur["detect"], callback=connecteur["callback"], bouncetime=200)
        self.fermer_valve()
        self.NIVEAU = self.mesurer_niveau()
        if self.NIVEAU < self.NORMAL:
            self.ouvrir_valve()
        self.afficher_niveau()
        self.kafka_config = obtenirConfigurationsProducteurDepuisVariablesEnvironnement() if 'BOOTSTRAP_SERVERS' in os.environ else {}
        self.producteur = creerProducteur(config=self.kafka_config) if "bootstrap.servers" in self.kafka_config else None
        os.system('sudo modprobe w1-gpio')
        os.system('sudo modprobe w1-therm')
        

    def afficher_niveau(self, niveau=None):
        if niveau is None:
            niveau = self.NIVEAU
        if niveau == self.MIN:
            logging.info("Le niveau est sous le niveau minimum.")
        elif niveau == self.BAS:
            logging.info("Le niveau est bas.")
        elif niveau == self.NORMAL:
            logging.info("Le niveau est normal")
        elif niveau == self.HAUT:
            logging.info("Le niveau est haut.")
        elif niveau == self.MAX:
            logging.info("Le niveau est au dessus du niveau maximum.")
        else:
            logging.error("Le niveau est inconnu, verifier le systeme.")
            
    def alerter_changement_niveau(self, niveau=None):
        if niveau is None:
            niveau = self.NIVEAU
        if niveau == self.MIN:
            self.lancer_alerte_min()
        elif niveau == self.BAS:
            self.lancer_alerte_bas()
        elif niveau == self.NORMAL:
            self.lancer_alerte_normal()
        elif niveau == self.HAUT:
            self.lancer_alerte_haut()
        elif niveau == self.MAX:
            self.lancer_alerte_max()
        else:
            self.lancer_erreur_niveau()

    def publier_niveau(self, msg, alerte=False):
        if self.producteur is not None:
            maintenant = self.maintenant()
            message = {}
            message["key"] = maintenant
            message["value"] = {}
            message["value"]["timestamp"] = maintenant
            message["value"]["niveau"] = self.NIVEAU
            message["value"]["message"] = msg
            publierMessage(producteur=self.producteur,message=message,topic=self.topic_niveau,logger=logging)
            if alerte:
                publierMessage(producteur=self.producteur,message=message,topic=self.topic_alerte,logger=logging)

    def lancer_alerte_vide(self):
        msg = "Alerte, Le chaudron est vide."
        logging.warning(msg=msg)
        self.publier_niveau(msg=msg, alerte=True)
            

    def lancer_alerte_min(self):
        msg = "Alerte, Le reservoir est au niveau minimum."
        logging.warning(msg=msg)
        self.publier_niveau(msg=msg, alerte=True)
        
    def lancer_alerte_bas(self):
        msg = "Alerte, Le reservoir est bas."
        logging.info(msg=msg)
        self.publier_niveau(msg=msg,alerte=False)
        
        
    def lancer_alerte_normal(self):
        msg = "Alerte, Le niveau du reservoir est normal pour le bouillage"
        logging.info(msg=msg)
        self.publier_niveau(msg=msg, alerte=False)
        
    def lancer_alerte_haut(self):
        msg = "Le niveau du reservoir est haut."
        logging.info(msg=msg)
        self.publier_niveau(msg=msg, alerte=False)

    def lancer_alerte_max(self):
        msg = "Alerte, le niveau maximal est atteint, il y a probablement un probleme avec la valve."
        logging.warning(msg=msg)
        self.publier_niveau(msg=msg, alerte=True)

    def lancer_erreur_niveau(self):
        msg = "Alerte Les informations de niveau sont incoherents. Il doit y avoir un probleme avec la sonde."
        logging.error(msg=msg)
        self.publier_niveau(msg=msg, alerte=True)

    def ouvrir_valve(self):
        logging.info("Ouvrir la valve pour ajouter de l'eau.")
        if not self.valve_en_action and not self.valve_ouverte:
            self.valve_en_action = True
            GPIO.output(self.OUVRIR_VALVE, GPIO.HIGH)
            sleep(self.temps_signal_valve)
            GPIO.output(self.OUVRIR_VALVE, GPIO.LOW)
            self.valve_en_action = False
            self.valve_ouverte = True
        
    def fermer_valve(self):
        logging.info("Fermer le valve.")
        if not self.valve_en_action and self.valve_ouverte:
            self.valve_en_action = True
            GPIO.output(self.FERMER_VALVE, GPIO.HIGH)
            sleep(self.temps_signal_valve)
            GPIO.output(self.FERMER_VALVE, GPIO.LOW)
            self.valve_en_action = False
            self.valve_ouverte = False
            

    def traiter_event_detect_pour_sonde_niveau(self, channel=None):
        nouveau_niveau = self.mesurer_niveau()

        if nouveau_niveau != self.NIVEAU and nouveau_niveau != self.ERREUR:
            if nouveau_niveau < self.NIVEAU and nouveau_niveau <= self.BAS:
                self.ouvrir_valve()
            elif nouveau_niveau > self.NIVEAU and nouveau_niveau >= self.HAUT:
                self.fermer_valve()
            self.afficher_niveau(niveau=nouveau_niveau)
            self.alerter_changement_niveau(niveau=nouveau_niveau)
        self.NIVEAU = nouveau_niveau
            

    def mesurer_niveau(self):
        etat_niv_min = GPIO.input(self.NIV_MIN_R)
        etat_niv_bas = GPIO.input(self.NIV_BAS_R)
        etat_niv_haut = GPIO.input(self.NIV_HAUT_R)
        etat_niv_max = GPIO.input(self.NIV_MAX_R)
        if etat_niv_max:
            return self.MAX
        elif etat_niv_haut:
            return self.HAUT
        elif etat_niv_bas:
            return self.NORMAL
        elif etat_niv_min:
            return self.BAS
        else:
            return self.MIN

    def lire_temperature(self):
        base_dir = '/sys/bus/w1/devices/'
        device_folder = glob.glob(base_dir + '28*')[0]
        device_file = device_folder + '/temperature'	
        while True:
            f = open(device_file, 'r')
            lines = f.readlines()
            f.close()
            temperature = int(lines[0])/1000
            logging.info("La temperature est: {0}".format(temperature))
            if self.producteur is not None:
                message = {}
                maintenant = self.maintenant()
                message["key"] = maintenant
                message["value"] = temperature
                publierMessage(producteur=self.producteur, message=message, topic=self.topic_temp, logger=logging)
            sleep(60)
            
    def maintenant(self):
        str_maintenant = strftime("%Y-%m-%d:%H:%M:%S", localtime())
        return str_maintenant
    
def signal_handler(sig, frame):
        GPIO.cleanup()
        sys.exit(0)

def main():
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(
        format=format,
        level=logging.INFO,
        datefmt="%H:%M:%S")

    ctrl_cmd = NiveauCtrlCmd()
    signal.signal(signal.SIGINT, signal_handler)
    temp_thread = threading.Thread(target=ctrl_cmd.lire_temperature)
    temp_thread.start()
    #signal.pause()

if __name__ == "__main__":
    main()
