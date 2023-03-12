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
import argparse

class NiveauCtrlCmd:
    NIV_MIN_R = 5 # 29
    NIV_MIN_F = 12 # 32
    NIV_BAS_R = 17 # 11
    NIV_BAS_F = 23 # 16
    NIV_HAUT_R = 27 # 13
    NIV_HAUT_F = 24 # 18
    NIV_MAX_R = 22 # 15
    NIV_MAX_F = 25 # 22
    POMPE = 26 # 37
    ERREUR = -1
    VIDE = 0
    MIN = 1
    BAS = 2
    NORMAL = 3
    HAUT = 4
    MAX = 5
    NIVEAU = 0
    info_niveaux = [
        {
            "niveau": VIDE,
            "alerte": True,
            "display": "VIDE",
            "message": "Le chaudron est vide"
        },
        {
            "niveau": MIN,
            "alerte": True,
            "display": "MIN",
            "message": "Le niveau du chaudron est au minimum"
        },
        {
            "niveau": BAS,
            "alerte": False,
            "display": "BAS",
            "message": "Le niveau du chaudron est bas"
        },
        {
            "niveau": NORMAL,
            "alerte": False,
            "display": "NORMAL",
            "message": "Le niveau du chaudron est normal pour le bouillage"
        },
        {
            "niveau": HAUT,
            "alerte": False,
            "display": "HAUT",
            "message": "Le niveau du chaudron est haut"
        },
        {
            "niveau": MAX,
            "alerte": True,
            "display": "MAX",
            "message": "Le niveau du chaudron est au maximum, vérifier la pompe."
        }
    ]
    MODE = GPIO.BCM # GPIO.BOARD
    topic_niveau = "bouillage.niveau"
    topic_alerte = "bouillage.alertes"
    topic_temp = "bouillage.temperature"
    producteur = None
    logger = None
    last_event = None
    
    def __init__(self, log_level=logging.INFO):
        format = "%(asctime)s: %(message)s"
        logging.basicConfig(
            format=format,
            level=log_level,
            encoding='utf-8',
            datefmt="%H:%M:%S")
        self.logger=logging.getLogger('bouillage_controle')
        self.logger.setLevel(log_level)

        self.pompe_en_action = False
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
                "numero": self.POMPE,
                "nom": "POMPE",
                "mode": GPIO.OUT,
                "initial": GPIO.HIGH
            }
        ]
        self.logger.info("setmode: {0}".format(self.MODE))
        GPIO.setmode(self.MODE)

        for connecteur in self.connecteurs:
            self.logger.info ("setup connecteur {0} mode: {1}".format(
                connecteur["numero"], 
                connecteur["mode"]))
            if connecteur["mode"] == GPIO.IN:
                pull_up_down = connecteur["pull_up_down"] if "pull_up_down" in connecteur else GPIO.PUD_DOWN
                GPIO.setup(connecteur["numero"], connecteur["mode"], pull_up_down=pull_up_down)
            elif connecteur["mode"] == GPIO.OUT:
                initial = connecteur["initial"] if "initial" in connecteur else GPIO.LOW
                GPIO.setup(connecteur["numero"], connecteur["mode"], initial=initial)

        self.arreter_pompe()
        self.NIVEAU = self.mesurer_niveau()
        if self.NIVEAU < self.NORMAL:
            self.demarrer_pompe()
        self.afficher_niveau()
        self.kafka_config = obtenirConfigurationsProducteurDepuisVariablesEnvironnement() if 'BOOTSTRAP_SERVERS' in os.environ else {}
        self.producteur = creerProducteur(config=self.kafka_config) if "bootstrap.servers" in self.kafka_config else None
        os.system('sudo modprobe w1-gpio')
        os.system('sudo modprobe w1-therm')
        self.publier_niveau(niveau=self.NIVEAU)
        for connecteur in self.connecteurs:
            if connecteur["mode"] == GPIO.IN:
                if "callback" in connecteur and "detect" in connecteur:
                    self.logger.info ("add_event_detect connecteur: {0}, detect {1}, callback : {2}".format(
                        connecteur["numero"], 
                        connecteur["detect"],
                        connecteur["callback"]))
                    GPIO.add_event_detect(connecteur["numero"], connecteur["detect"], callback=connecteur["callback"], bouncetime=200)
        

    def afficher_niveau(self, niveau=None):
        if niveau is None:
            niveau = self.NIVEAU

        if self.info_niveaux[niveau]["alerte"]:
            self.logger.warning("Niveau: {niveau} {message}".format(niveau=self.info_niveaux[niveau]["display"], message=self.info_niveaux[niveau]["message"]))
        else:
            self.logger.info("Niveau: {niveau} {message}".format(niveau=self.info_niveaux[niveau]["display"], message=self.info_niveaux[niveau]["message"]))
            

    def publier_niveau(self, niveau=None):
        if niveau is None:
            niveau = self.NIVEAU

        if self.producteur is not None:
            maintenant = self.maintenant()
            message = {}
            message["key"] = maintenant
            message["value"] = self.info_niveaux[niveau]
            publierMessage(producteur=self.producteur,message=message,topic=self.topic_niveau,logger=self.logger)
            if self.info_niveaux[niveau]["alerte"]:
                publierMessage(producteur=self.producteur,message=message,topic=self.topic_alerte,logger=self.logger)

    def demarrer_pompe(self):
        self.logger.info("Démarrer la pompe pour ajouter de l'eau.")
        if not self.pompe_en_action:
            GPIO.output(self.POMPE, GPIO.LOW)
            self.pompe_en_action = True
        
    def arreter_pompe(self):
        self.logger.info("Arrêter la pompe.")
        if self.pompe_en_action:
            GPIO.output(self.POMPE, GPIO.HIGH)
            self.pompe_en_action = False
            

    def traiter_event_detect_pour_sonde_niveau(self, channel=None):
        self.logger.debug("traiter_event_detect_pour_sonde_niveau channel: {channel}".format(channel=channel))
        nouveau_niveau = self.mesurer_niveau(channel=channel)
        msg = "Niveau avant mesure: {0}. Nouveau niveau {1}".format(self.NIVEAU, nouveau_niveau)
        self.logger.info(msg)

        if nouveau_niveau != self.NIVEAU and nouveau_niveau != self.ERREUR:
            if nouveau_niveau < self.NIVEAU and nouveau_niveau <= self.BAS:
                self.demarrer_pompe()
            elif nouveau_niveau > self.NIVEAU and nouveau_niveau >= self.HAUT:
                self.arreter_pompe()
            self.afficher_niveau(niveau=nouveau_niveau)
            self.publier_niveau(niveau=nouveau_niveau)
        self.NIVEAU = nouveau_niveau
            

    def mesurer_niveau(self, channel=None):
        etat_niv_min = GPIO.input(self.NIV_MIN_R)
        self.logger.debug("etat_niv_min={}".format(etat_niv_min))
        etat_niv_min_f = GPIO.input(self.NIV_MIN_F)
        self.logger.debug("etat_niv_min_f={}".format(etat_niv_min_f))
        etat_niv_bas = GPIO.input(self.NIV_BAS_R)
        self.logger.debug("etat_niv_bas={}".format(etat_niv_bas))
        etat_niv_bas_f = GPIO.input(self.NIV_BAS_F)
        self.logger.debug("etat_niv_bas_f={}".format(etat_niv_bas_f))
        etat_niv_haut = GPIO.input(self.NIV_HAUT_R)
        self.logger.debug("etat_niv_haut={}".format(etat_niv_haut))
        etat_niv_haut_f = GPIO.input(self.NIV_HAUT_F)
        self.logger.debug("etat_niv_haut_f={}".format(etat_niv_haut_f))
        etat_niv_max = GPIO.input(self.NIV_MAX_R)
        self.logger.debug("etat_niv_max={}".format(etat_niv_max))
        etat_niv_max_f = GPIO.input(self.NIV_MAX_F)
        self.logger.debug("etat_niv_max_f={}".format(etat_niv_max_f))

        niveau = None
        if etat_niv_max:
            niveau = self.MAX
        elif etat_niv_haut:
            niveau = self.HAUT
        elif etat_niv_bas:
            niveau = self.NORMAL
        elif etat_niv_min:
            niveau = self.BAS
        else:
            niveau = self.MIN

        if ((channel == self.NIV_MIN_F and etat_niv_min_f == 0) or
            (channel == self.NIV_MIN_R and etat_niv_min == 0) or
            (channel == self.NIV_BAS_F and etat_niv_bas_f == 0) or    
            (channel == self.NIV_BAS_R and etat_niv_bas == 0) or
            (channel == self.NIV_HAUT_F and etat_niv_haut_f == 0) or    
            (channel == self.NIV_HAUT_R and etat_niv_haut == 0) or
            (channel == self.NIV_MAX_F and etat_niv_max_f == 0) or    
            (channel == self.NIV_MAX_R and etat_niv_max == 0)):
            self.direction = "descendant"
        else:
            self.direction = "montant"

        self.last_event = channel
        self.logger.debug("Direction: {direction}".format(direction=self.direction))
        self.logger.debug("Etat pompe en action: {pompe}".format(pompe=self.pompe_en_action))
        if self.direction == "montant" and not self.pompe_en_action:
            self.logger.warning("Alerte, le niveau monte et la pompe n'est pas en action") 
        if self.direction == "descendant" and self.pompe_en_action:
            self.logger.warning("Alerte, le niveau descend et la pompe est en action")

        return niveau

    def lire_temperature(self):
        while True:
            lines = []
            base_dir = '/sys/bus/w1/devices/'
            device_folders = glob.glob(base_dir + '28*')
            if len(device_folders) > 0:
                device_folder = device_folders[0]
                device_file = device_folder + '/temperature'
                self.logger.info("Le fichier de température est {}".format(device_file))
                max_tries = 10
                for tried in range(max_tries):
                    try:
                        f = open(device_file, 'r')
                        lines = f.readlines()
                        f.close()
                    except FileNotFoundError:
                        if tried < max_tries - 1:
                            sleep(1)
                            continue
                        else:
                            self.logger.error("Le fichier n'est pas disponible pour la sonde de temperature")
                    break

            if len(lines) > 0:
                temperature = int(lines[0])/1000
                self.logger.info("La temperature est: {0}".format(temperature))
                if self.producteur is not None:
                    message = {}
                    maintenant = self.maintenant()
                    message["key"] = maintenant.encode()
                    message["value"] = str(temperature).encode()
                    publierMessage(producteur=self.producteur, message=message, topic=self.topic_temp, logger=logging)
            else:
                print("La sonde n'a pas retourné de température")
            sleep(60)
            
    def maintenant(self):
        str_maintenant = strftime("%Y-%m-%d:%H:%M:%S", localtime())
        return str_maintenant

parser = argparse.ArgumentParser()
parser.add_argument( '-log',
                    '--loglevel',
                    default='info',
                    help='Provide logging level. Example --loglevel debug, default=info' )

args = parser.parse_args()

ctrl_cmd = NiveauCtrlCmd(log_level=args.loglevel.upper())

def signal_handler(sig, frame):
    ctrl_cmd.arreter_pompe()
    GPIO.cleanup()
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    temp_thread = threading.Thread(target=ctrl_cmd.lire_temperature)
    temp_thread.start()

if __name__ == "__main__":
    main()
