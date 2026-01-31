#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import glob
from time import localtime, strftime, sleep
try:
    import RPi.GPIO as GPIO
except ImportError:
    import Mock.GPIO as GPIO
import logging
import os
from inspqkafka.producteur import obtenirConfigurationsProducteurDepuisVariablesEnvironnement, creerProducteur, publierMessage

from statistics import mean, pstdev

class NiveauCtrlCmd:
    BROCHE_NIV_1 = 12 # 32
    BROCHE_NIV_2 = 5 # 29
    BROCHE_NIV_3 = 25 # 22
    BROCHE_NIV_4 = 22 # 15
    BROCHE_NIV_5 = 24 # 18
    BROCHE_NIV_6 = 27 # 13
    BROCHE_NIV_7 = 23 # 16
    BROCHE_NIV_8 = 17 # 11
    BROCHE_POMPE = 26 # 37
    BROCHE_TONNE = 16 # 36
    ERREUR = -1
    VIDE = 0
    BAS = 1
    HAUT = 3
    MAX = 8
    NIVEAU = 0
    info_niveaux = [
        {
            "niveau": VIDE,
            "alerte": True,
            "display": "VIDE",
            "message": "Le chaudron est vide"
        },
        {
            "niveau": 1,
            "alerte": True,
            "display": "1-2",
            "message": "Niveau entre 1 et 2 pouces",
            "broche": BROCHE_NIV_1
        },
        {
            "niveau": 2,
            "alerte": False,
            "display": "2-3",
            "message": "Niveau entre 2 et 3 pouces",
            "broche": BROCHE_NIV_2
        },
        {
            "niveau": 3,
            "alerte": False,
            "display": "3-4",
            "message": "Niveau entre 3 et 4 pouces",
            "broche": BROCHE_NIV_3
        },
        {
            "niveau": 4,
            "alerte": False,
            "display": "4-5",
            "message": "Niveau entre 4 et 5 pouces",
            "broche": BROCHE_NIV_4
        },
        {
            "niveau": 5,
            "alerte": True,
            "display": "5-6",
            "message": "Niveau entre 5 et 6 pouces",
            "broche": BROCHE_NIV_5
        },
        {
            "niveau": 6,
            "alerte": True,
            "display": "6-7",
            "message": "Niveau entre 6 et 7 pouces",
            "broche": BROCHE_NIV_6
        },
        {
            "niveau": 7,
            "alerte": True,
            "display": "7-8",
            "message": "Niveau entre 7 et 8 pouces",
            "broche": BROCHE_NIV_7
        },
        {
            "niveau": 8,
            "alerte": True,
            "display": "8+",
            "message": "Niveau pls de 8 pouces",
            "broche": BROCHE_NIV_8
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
    message_alerte_niveau_monte_pompe_off = {
        "niveau": 0,
        "alerte": True,
        "display": "NIV_UP_PUMP_OFF",
        "message": "Le niveau baisse mais la pompe fonctionne"
    }
    message_alerte_niveau_baisse_pompe_on = {
        "niveau": 0,
        "alerte": True,
        "display": "NIV_DOWN_PUMP_ON",
        "message": "Le niveau baisse mais la pompe fonctionne"
    }
    dernieres_temperatures = []
    nb_mesures_temp_pour_calcule_base = 5
    ecart_pour_fin_bouillage = 4
    temperature_base = None
    
    
    def __init__(self,
                 log_level=logging.INFO,
                 niveau_bas=BAS,
                 niveau_haut=HAUT,
                 niveau_max=MAX,
                 log_path="/var/log",
                 log_file_name="cabanasucre",
                 modprobe=True):
        self.log_path = log_path
        self.log_file_name = log_file_name
        format = "%(asctime)s: %(message)s"
        logging.basicConfig(
            format=format,
            level=log_level,
            encoding='utf-8',
            datefmt="%H:%M:%S")
        self.logger=logging.getLogger('bouillage_controle')
        self.logger.setLevel(log_level)
        fileHandler = logging.FileHandler("{0}/{1}.log".format(self.log_path, self.log_file_name))
        self.logger.addHandler(fileHandler)
        self.BAS = niveau_bas
        self.logger.info("Le niveau bas est {}".format(self.BAS))
        self.HAUT = niveau_haut
        self.logger.info("Le niveau haut est {}".format(self.HAUT))
        self.MAX = niveau_max
        self.logger.info("Le niveau maximum est {}".format(self.MAX))

        self.pompe_en_action = False
        self.connecteurs = [
            {
                "numero": self.BROCHE_TONNE,
                "nom": "TONNE",
                "mode": GPIO.IN,
                "detect": GPIO.BOTH,
                "callback": self.traiter_event_detect_pour_sonde_tonne,
                "pull_up_down": GPIO.PUD_DOWN
            },
            {
                "numero": self.BROCHE_POMPE,
                "nom": "POMPE",
                "mode": GPIO.OUT,
                "initial": GPIO.LOW
            }
        ]
        self.logger.info("setmode: {0}".format(self.MODE))
        GPIO.setmode(self.MODE)
        # Initier tous les connecteurs de niveaux
        mode = GPIO.IN
        detect = GPIO.BOTH
        pull_up_down = GPIO.PUD_DOWN
        callback = self.traiter_event_detect_pour_sonde_niveau
        for connecteur in self.info_niveaux:
            if "broche" in connecteur:
                self.logger.info ("setup connecteur {0} mode: {1}".format(
                    connecteur["broche"], 
                    mode))
                GPIO.setup(connecteur["broche"], mode, pull_up_down=pull_up_down)
                self.logger.info ("add_event_detect connecteur: {0}, detect {1}, callback : {2}".format(
                    connecteur["broche"], 
                    detect,
                    callback))
                GPIO.add_event_detect(connecteur["broche"], detect, callback=callback, bouncetime=200)
        # Initier les autres connecteurs
        for connecteur in self.connecteurs:
            self.logger.info ("setup connecteur {0} mode: {1}".format(
                connecteur["numero"], 
                connecteur["mode"]))
            if connecteur["mode"] == GPIO.IN:
                pull_up_down = connecteur["pull_up_down"] if "pull_up_down" in connecteur else GPIO.PUD_DOWN
                GPIO.setup(connecteur["numero"], connecteur["mode"], pull_up_down=pull_up_down)
                if "callback" in connecteur and "detect" in connecteur:
                    self.logger.info ("add_event_detect connecteur: {0}, detect {1}, callback : {2}".format(
                        connecteur["numero"], 
                        connecteur["detect"],
                        connecteur["callback"]))
                    GPIO.add_event_detect(connecteur["numero"], connecteur["detect"], callback=connecteur["callback"], bouncetime=200)
            elif connecteur["mode"] == GPIO.OUT:
                initial = connecteur["initial"] if "initial" in connecteur else GPIO.LOW
                GPIO.setup(connecteur["numero"], connecteur["mode"], initial=initial)

        self.arreter_pompe()
        self.verifier_niveau_tonne()
        self.NIVEAU = self.mesurer_niveau()
        if self.NIVEAU < self.BAS:
            self.demarrer_pompe()
        self.afficher_niveau()
        self.kafka_config = obtenirConfigurationsProducteurDepuisVariablesEnvironnement() if 'BOOTSTRAP_SERVERS' in os.environ else {}
        self.producteur = creerProducteur(config=self.kafka_config) if "bootstrap.servers" in self.kafka_config else None
        if modprobe:
            os.system('sudo modprobe w1-gpio')
            os.system('sudo modprobe w1-therm')
        self.publier_niveau(niveau=self.NIVEAU)
        

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
                alerte['display'] = "NIV: {niveau}".format(niveau=self.info_niveaux[niveau]["display"])
                self.publier_alerte(contenu_message=alerte)
                
    def demarrer_pompe(self):
        if self.pompe_enabled:
            if not self.pompe_en_action:
                self.logger.info("Démarrer la pompe pour ajouter de l'eau.")
                GPIO.output(self.BROCHE_POMPE, GPIO.HIGH)
                self.pompe_en_action = True
                self.publier_alerte(contenu_message=self.message_alerte_demarrage_pompe)
        else:
            self.logger.warning("Impossible de démarrer la pompe, il n'y a pas assez d'eau dans la tonne")
        
    def arreter_pompe(self):
        if self.pompe_en_action:
            self.logger.info("Arrêter la pompe.")
            GPIO.output(self.BROCHE_POMPE, GPIO.LOW)
            self.pompe_en_action = False
            self.publier_alerte(contenu_message=self.message_alerte_arret_pompe)
            

    def traiter_event_detect_pour_sonde_niveau(self, channel=None):
        self.logger.debug("traiter_event_detect_pour_sonde_niveau channel: {channel}".format(channel=channel))
        nouveau_niveau = self.mesurer_niveau(channel=channel)
        if nouveau_niveau != self.NIVEAU:
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
        etat_connecteurs = []
        for connecteur in self.info_niveaux:
            if "broche" in connecteur:
                etat_niveau = {}
                etat_niveau["niveau"] = connecteur["niveau"]
                etat_niveau["etat"] = GPIO.input(connecteur["broche"])
                etat_connecteurs.append(etat_niveau)
                self.logger.debug("etat niv {niveau}: {etat}".format(niveau=connecteur["display"], etat=etat_niveau["etat"]))    
        self.logger.debug("Etat connecteur: {}".format(str(etat_connecteurs)))
        # Trouver la sonde la plus haute dont l'état est 1
        niveau = self.VIDE
        i = len(etat_connecteurs)
        while i > 0:
            i = i - 1
            if etat_connecteurs[i]["etat"]:
                niveau = etat_connecteurs[i]["niveau"]
                break
        niveau_sonde_channel = None
        # Trouver le niveau associé à la broche qui a provoqué l'appel
        for info_niveau in self.info_niveaux:
            if ("broche" in info_niveau and channel == info_niveau["broche"]):
                niveau_sonde_channel = info_niveau["niveau"]
                break;
        if niveau > self.NIVEAU:
            self.direction = "montant"
        elif niveau < self.NIVEAU:
                self.direction = "descendant"
        else:
            self.direction = "stable"

        self.last_event = channel
        self.logger.debug("Direction: {direction}".format(direction=self.direction))
        self.logger.debug("Etat pompe en action: {pompe}".format(pompe=self.pompe_en_action))
        if self.direction == "montant" and not self.pompe_en_action:
            self.logger.warning("Alerte, le niveau monte et la pompe n'est pas en action")
            alerte = self.message_alerte_niveau_monte_pompe_off.copy()
            alerte['niveau'] = niveau
            self.publier_alerte(contenu_message=alerte)
        if self.direction == "descendant" and self.pompe_en_action:
            self.logger.warning("Alerte, le niveau descend et la pompe est en action")
            alerte = self.message_alerte_niveau_baisse_pompe_on.copy()
            alerte['niveau'] = niveau
            self.publier_alerte(contenu_message=alerte)

        return niveau

    def traiter_event_detect_pour_sonde_tonne(self, channel=None):
        self.logger.debug("traiter_event_detect_pour_sonde_tonne channel: {channel}".format(channel=channel))
        if channel is not None and channel == self.BROCHE_TONNE:
            self.verifier_niveau_tonne()

    def verifier_niveau_tonne(self):
        sonde_niveau_tonne = GPIO.input(self.BROCHE_TONNE)
        self.logger.debug("Sonde niveau tonne: {}".format(sonde_niveau_tonne))
        if sonde_niveau_tonne:
            self.logger.debug("Il y a de l'eau dans la tonne")
            self.pompe_enabled = True
            self.mesurer_niveau()
            if self.NIVEAU < self.BAS:
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

