#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import signal
import sys
import RPi.GPIO as GPIO
import logging
import threading
import os
from inspqcommun.kafka.consommateur import obtenirConfigurationsConsommateurDepuisVariablesEnvironnement, decode_from_bytes
from confluent_kafka import OFFSET_END, Consumer
import drivers
import argparse
from statistics import mean, pstdev

class ConsoleSucrier:
    topic_niveau = "bouillage.niveau"
    topic_alerte = "bouillage.alertes"
    topic_temp = "bouillage.temperature"
    logger = None
    consommateur = None
    ligne_niveau = 1
    ligne_temp = 2
    ligne_alerte = 2
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
        self.logger=logging.getLogger('console_sucrier')
        self.logger.setLevel(log_level)

        GPIO.setmode(GPIO.BCM)
        self.kafka_config = obtenirConfigurationsConsommateurDepuisVariablesEnvironnement(logger=self.logger) if 'BOOTSTRAP_SERVERS' in os.environ else None
        if self.kafka_config is not None:
            self.kafka_config.kafka['auto.offset.reset'] = OFFSET_END
            liste_topics = [self.topic_alerte, self.topic_niveau, self.topic_temp]
            self.consommateur = Consumer(self.kafka_config.kafka)
            self.consommateur.subscribe(liste_topics, on_assign=self.reset_offset)
        self.display = drivers.Lcd()
        self.afficher_message_accueil()

    def reset_offset(self, consumer, partitions):
        for p in partitions:
            p.offset = OFFSET_END
        consumer.assign(partitions)

    def consommer_messages(self):
        if self.consommateur is None:
            return
        while True:
            msg = self.consommateur.poll(timeout=0.1)
            if msg is not None:
                if msg.error():
                    self.logger.error("Erreur Kafka: {0} {1}".format(msg.error().code(), msg.error().str()))
                if msg.topic() == self.topic_temp:
                    self.traiter_temperature(key=decode_from_bytes(msg.key()), value=decode_from_bytes(msg.value()))
                elif msg.topic() == self.topic_niveau:
                    self.afficher_niveau(key=decode_from_bytes(msg.key()), value=decode_from_bytes(msg.value()))
                elif msg.topic() == self.topic_alerte:
                    self.lancer_alerte(key=decode_from_bytes(msg.key()), value=decode_from_bytes(msg.value()))

    def traiter_temperature(self, key, value):
        self.logger.info("{0}: Temperature: {1}".format(key, value))
        self.display.lcd_display_string("Temp: {temp} C".format(temp=value).ljust(16),
                                        self.ligne_temp)
        if self.temperature_base is None:
            self.calculer_temperature_base(temp=value)
        elif value > self.temperature_base + self.ecart_pour_fin_bouillage:
            self.logger.warning("La temperature de bouillage est atteinte {temp}".format(temp=value))
            self.display.lcd_display_string("Fin boil {temp}".format(temp=value).ljust(16),
                                            self.ligne_alerte)
        elif value < self.temperature_base - 0.5:
            self.logger.warning("La temperature est sous la temperature de base {temp}".format(temp=value))
            self.display.lcd_display_string("Tmp basse {temp}".format(temp=value).ljust(16),
                                            self.ligne_alerte)

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

    def afficher_niveau(self, key, value):
        self.logger.info("{0}: Niveau: {1} {2}".format(key, value['niveau'], value['message']))
        type = 'Alerte' if value["alerte"] else 'Niveau'
        self.display.lcd_display_string("{type}: {niveau}".format(type=type,
                                                                  niveau=value['display']).ljust(16),
                                        self.ligne_niveau)

    def lancer_alerte(self, key, value):
        self.logger.warning("{0}: Alerte niveau: {1} {2}".format(key, value['niveau'], value['message']))

    def afficher_message_accueil(self):
        message_ligne_1 = "Console Sucrier".ljust(16)
        message_ligne_2 = "Attente msg...".ljust(16)
        self.logger.info(message_ligne_1 + ' ' + message_ligne_2)
        self.display.lcd_display_string(message_ligne_1, 1)
        self.display.lcd_display_string(message_ligne_2, 2)
    
parser = argparse.ArgumentParser()
parser.add_argument( '-log',
                    '--loglevel',
                    default='info',
                    help='Provide logging level. Example --loglevel debug, default=info' )

args = parser.parse_args()
sucrier = ConsoleSucrier(log_level=args.loglevel.upper())

def signal_handler(sig, frame):
        GPIO.cleanup()
        sucrier.display.lcd_clear()
        sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    consumer_thread = threading.Thread(target=sucrier.consommer_messages)
    consumer_thread.start()

if __name__ == "__main__":
    main()
