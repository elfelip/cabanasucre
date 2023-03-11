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
    MODE = GPIO.BCM # GPIO.BOARD
    topic_niveau = "bouillage.niveau"
    topic_alerte = "bouillage.alertes"
    topic_temp = "bouillage.temperature"
    producteur = None
    logger = None
    
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
        self.alerter_changement_niveau(niveau=self.NIVEAU)
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
        if niveau == self.VIDE:
            self.logger.info("Le chaudron est presque vide")
        elif niveau == self.MIN:
            self.logger.info("Le niveau est sous le niveau minimum.")
        elif niveau == self.BAS:
            self.logger.info("Le niveau est bas.")
        elif niveau == self.NORMAL:
            self.logger.info("Le niveau est normal")
        elif niveau == self.HAUT:
            self.logger.info("Le niveau est haut.")
        elif niveau == self.MAX:
            self.logger.info("Le niveau est au dessus du niveau maximum.")
        else:
            self.logger.error("Le niveau est inconnu, verifier le systeme.")
            
    def alerter_changement_niveau(self, niveau=None):
        if niveau is None:
            niveau = self.NIVEAU
        if niveau == self.VIDE:
            self.lancer_alerte_vide()
        elif niveau == self.MIN:
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
            publierMessage(producteur=self.producteur,message=message,topic=self.topic_niveau,logger=self.logger)
            if alerte:
                publierMessage(producteur=self.producteur,message=message,topic=self.topic_alerte,logger=self.logger)

    def lancer_alerte_vide(self):
        msg = "Alerte, Le chaudron est vide."
        self.logger.warning(msg=msg)
        self.publier_niveau(msg=msg, alerte=True)
            

    def lancer_alerte_min(self):
        msg = "Alerte, Le reservoir est au niveau minimum."
        self.logger.warning(msg=msg)
        self.publier_niveau(msg=msg, alerte=True)
        
    def lancer_alerte_bas(self):
        msg = "Le reservoir est bas."
        self.logger.info(msg=msg)
        self.publier_niveau(msg=msg,alerte=False)
        
        
    def lancer_alerte_normal(self):
        msg = "Le niveau du reservoir est normal pour le bouillage"
        self.logger.info(msg=msg)
        self.publier_niveau(msg=msg, alerte=False)
        
    def lancer_alerte_haut(self):
        msg = "Le niveau du reservoir est haut."
        self.logger.info(msg=msg)
        self.publier_niveau(msg=msg, alerte=False)

    def lancer_alerte_max(self):
        msg = "Alerte, le niveau maximal est atteint, il y a probablement un probleme avec la pompe."
        self.logger.warning(msg=msg)
        self.publier_niveau(msg=msg, alerte=True)

    def lancer_erreur_niveau(self):
        msg = "Alerte Les informations de niveau sont incoherents. Il doit y avoir un probleme avec la sonde."
        self.logger.error(msg=msg)
        self.publier_niveau(msg=msg, alerte=True)

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
        nouveau_niveau = self.mesurer_niveau()
        msg = "Niveau avant mesure: {0}. Nouveau niveau {1}".format(self.NIVEAU, nouveau_niveau)
        self.logger.info(msg)

        if nouveau_niveau != self.NIVEAU and nouveau_niveau != self.ERREUR:
            if nouveau_niveau < self.NIVEAU and nouveau_niveau <= self.BAS:
                self.demarrer_pompe()
            elif nouveau_niveau > self.NIVEAU and nouveau_niveau >= self.HAUT:
                self.arreter_pompe()
            self.afficher_niveau(niveau=nouveau_niveau)
            self.alerter_changement_niveau(niveau=nouveau_niveau)
        self.NIVEAU = nouveau_niveau
            

    def mesurer_niveau(self):
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

ctrl_cmd = None

def signal_handler(sig, frame):
    ctrl_cmd.arreter_pompe()
    GPIO.cleanup()
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument( '-log',
                        '--loglevel',
                        default='info',
                        help='Provide logging level. Example --loglevel debug, default=info' )

    args = parser.parse_args()

    ctrl_cmd = NiveauCtrlCmd(log_level=args.loglevel.upper())
    signal.signal(signal.SIGINT, signal_handler)
    temp_thread = threading.Thread(target=ctrl_cmd.lire_temperature)
    temp_thread.start()
    #signal.pause()

if __name__ == "__main__":
    main()
