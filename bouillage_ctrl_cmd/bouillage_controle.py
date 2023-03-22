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
from statistics import mean, pstdev

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
    TONNE = 16 # 36
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
    pompe_enabled = False
    message_alerte_tonne_vide = {
        "niveau": 0,
        "alerte": True,
        "display": "TONNE_VIDE",
        "message": "La tonne est vide, la pompe est désactivée."
    }
    message_alerte_demarrage_pompe = {
        "niveau": BAS,
        "alerte": False,
        "display": "POMPE_ON",
        "message": "Démarrage de la pompe"
    }
    message_alerte_arret_pompe = {
        "niveau": HAUT,
        "alerte": False,
        "display": "POMPE_OFF",
        "message": "Arrêt de la pompe"
    }
    message_alerte_fin_bouillage = {
        "niveau": 0,
        "alerte": True,
        "display": "FIN_BOUIL",
        "message": "Fin du bouillage"
    }
    message_alerte_temperature_basse = {
        "niveau": 0,
        "alerte": True,
        "display": "BAS_TEMP",
        "message": "Température basse"
    }
    message_alerte_temperature_de_base_etablie = {
        "niveau": 0,
        "alerte": True,
        "display": "TEMP_BASE",
        "message": "La température de base de bouillage a été établie"
    }
    dernieres_temperatures = []
    nb_mesures_temp_pour_calcule_base = 3
    ecart_pour_fin_bouillage = 3
    temperature_base = None
    
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
                "detect": GPIO.BOTH,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_MIN_F,
                "nom": "NIV_MIN_F",
                "mode": GPIO.IN,
                "detect": GPIO.BOTH,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_BAS_R,
                "nom": "NIV_BAS_R",
                "mode": GPIO.IN,
                "detect": GPIO.BOTH,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_BAS_F,
                "nom": "NIV_BAS_F",
                "mode": GPIO.IN,
                "detect": GPIO.BOTH,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_HAUT_R,
                "nom": "NIV_HAUT_R",
                "mode": GPIO.IN,
                "detect": GPIO.BOTH,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_HAUT_F,
                "nom": "NIV_HAUT_F",
                "mode": GPIO.IN,
                "detect": GPIO.BOTH,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_MAX_R,
                "nom": "NIV_MAX_R",
                "mode": GPIO.IN,
                "detect": GPIO.BOTH,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.NIV_MAX_F,
                "nom": "NIV_MAX_F",
                "mode": GPIO.IN,
                "detect": GPIO.BOTH,
                "callback": self.traiter_event_detect_pour_sonde_niveau,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.TONNE,
                "nom": "TONNE",
                "mode": GPIO.IN,
                "detect": GPIO.BOTH,
                "callback": self.traiter_event_detect_pour_sonde_tonne,
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
        self.verifier_niveau_tonne()
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
                alerte = self.info_niveaux[niveau].copy()
                alerte['display'] = "NIV_{niveau}".format(niveau=self.info_niveaux[niveau]["display"])
                self.publier_alerte(contenu_message=alerte)
                
    def demarrer_pompe(self):
        if self.pompe_enabled:
            if not self.pompe_en_action:
                self.logger.info("Démarrer la pompe pour ajouter de l'eau.")
                GPIO.output(self.POMPE, GPIO.LOW)
                self.pompe_en_action = True
                self.publier_alerte(contenu_message=self.message_alerte_demarrage_pompe)
        else:
            self.logger.warning("Impossible de démarrer la pompe, il n'y a pas assez d'eau dans la tonne")
        
    def arreter_pompe(self):
        if self.pompe_en_action:
            self.logger.info("Arrêter la pompe.")
            GPIO.output(self.POMPE, GPIO.HIGH)
            self.pompe_en_action = False
            self.publier_alerte(contenu_message=self.message_alerte_arret_pompe)
            

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
        if etat_niv_max or etat_niv_max_f:
            niveau = self.MAX
        elif etat_niv_haut or etat_niv_haut_f:
            niveau = self.HAUT
        elif etat_niv_bas or etat_niv_bas_f:
            niveau = self.NORMAL
        elif etat_niv_min or etat_niv_min_f:
            niveau = self.BAS
        else:
            niveau = self.MIN

        if ((channel == self.NIV_MIN_F and etat_niv_min_f) or
            (channel == self.NIV_MIN_R and etat_niv_min) or
            (channel == self.NIV_BAS_F and etat_niv_bas_f) or    
            (channel == self.NIV_BAS_R and etat_niv_bas) or
            (channel == self.NIV_HAUT_F and etat_niv_haut_f) or    
            (channel == self.NIV_HAUT_R and etat_niv_haut) or
            (channel == self.NIV_MAX_F and etat_niv_max_f) or    
            (channel == self.NIV_MAX_R and etat_niv_max)):
            self.direction = "montant"
        else:
            self.direction = "descendant"

        self.last_event = channel
        self.logger.debug("Direction: {direction}".format(direction=self.direction))
        self.logger.debug("Etat pompe en action: {pompe}".format(pompe=self.pompe_en_action))
        if self.direction == "montant" and not self.pompe_en_action:
            self.logger.warning("Alerte, le niveau monte et la pompe n'est pas en action") 
        if self.direction == "descendant" and self.pompe_en_action:
            self.logger.warning("Alerte, le niveau descend et la pompe est en action")

        return niveau

    def traiter_event_detect_pour_sonde_tonne(self, channel=None):
        self.logger.debug("traiter_event_detect_pour_sonde_tonne channel: {channel}".format(channel=channel))
        if channel is not None and channel == self.TONNE:
            self.verifier_niveau_tonne()

    def verifier_niveau_tonne(self):
        sonde_niveau_tonne = GPIO.input(self.TONNE)
        self.logger.debug("Sonde niveau tonne: {}".format(sonde_niveau_tonne))
        if sonde_niveau_tonne:
            self.logger.info("Il y a de l'eau dans la tonne")
            self.pompe_enabled = True
            self.mesurer_niveau()
            if self.NIVEAU < self.NORMAL:
                self.demarrer_pompe()
        else:
            self.logger.warning("Il n'y a plus d'eau dans la tonne.")
            if self.pompe_en_action:
                self.arreter_pompe()
            self.pompe_enabled = False
            self.publier_alerte(contenu_message=self.message_alerte_tonne_vide)

    def publier_alerte(self, contenu_message):
        if self.producteur is not None:
            maintenant = self.maintenant()
            message = {}
            message["key"] = maintenant
            message["value"] = contenu_message
            publierMessage(producteur=self.producteur,message=message,topic=self.topic_alerte,logger=self.logger)

    def traiter_temperature(self, value):        
        if self.temperature_base is None:
            self.calculer_temperature_base(temp=value)
        elif value > self.temperature_base + self.ecart_pour_fin_bouillage:
            self.logger.warning("La temperature de fin de bouillage est atteinte {temp}".format(temp=value))
            alerte = self.message_alerte_fin_bouillage.copy()
            alerte['display'] = "{msg}: {temp} C".format(msg=alerte["display"], temp=value)
            self.publier_alerte(contenu_message=alerte)
        elif value < self.temperature_base - 0.5:
            self.logger.warning("La temperature est sous la temperature de base {temp}".format(temp=value))
            alerte = self.message_alerte_temperature_basse.copy()
            alerte['display'] = "{msg}: {temp} C".format(msg=alerte["display"], temp=value)
            self.publier_alerte(contenu_message=alerte)

    def calculer_temperature_base(self, temp):
        if len(self.dernieres_temperatures) < self.nb_mesures_temp_pour_calcule_base:
            self.logger.debug("Ajout {temp} dans dernieres temperatures".format(temp=temp))
            self.dernieres_temperatures.append(temp)
        else:
            self.logger.debug("Remplacer {temp1} par {temp2} dans dernieres temperatures".format(
                temp1=self.dernieres_temperatures[0],
                temp2=temp))
            for mesure in range(self.nb_mesures_temp_pour_calcule_base - 1):
                self.dernieres_temperatures[mesure] = self.dernieres_temperatures[mesure + 1]
            self.dernieres_temperatures[self.nb_mesures_temp_pour_calcule_base - 1] = temp

        if len(self.dernieres_temperatures) >= self.nb_mesures_temp_pour_calcule_base and temp > 95:
            ecart_type = pstdev(self.dernieres_temperatures)
            self.logger.debug("Ecart type temp: {ecart}".format(ecart=ecart_type))
            if ecart_type < 0.25:
                self.temperature_base = mean(self.dernieres_temperatures)
                self.logger.info("Temperature de base établi à {temp}".format(temp=self.temperature_base))
                alerte = self.message_alerte_temperature_de_base_etablie.copy()
                alerte['display'] = "{msg}: {temp} C".format(msg=alerte["display"], temp=self.temperature_base)
                self.publier_alerte(contenu_message=alerte)

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
                self.traiter_temperature(value=temperature)
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
