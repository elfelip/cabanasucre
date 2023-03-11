#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import signal
import sys
from time import localtime, strftime, sleep
import RPi.GPIO as GPIO
import logging
import threading
import os
from inspqcommun.kafka.consommateur import obtenirConfigurationsConsommateurDepuisVariablesEnvironnement, creerConsommateur, decode_from_bytes
from confluent_kafka import OFFSET_END, Consumer
import drivers
import argparse

class ConsoleSucrier:
    topic_niveau = "bouillage.niveau"
    topic_alerte = "bouillage.alertes"
    topic_temp = "bouillage.temperature"
    logger = None
    consommateur = None
    ligne_niveau = 1
    ligne_temp = 2
    ligne_alerte = 1

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

    # Set up a callback to handle the '--reset' flag.
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
                    self.afficher_temperature(key=decode_from_bytes(msg.key()), value=decode_from_bytes(msg.value()))
                elif msg.topic() == self.topic_niveau:
                    self.afficher_niveau(key=decode_from_bytes(msg.key()), value=decode_from_bytes(msg.value()))
                elif msg.topic() == self.topic_alerte:
                    self.afficher_alerte(key=decode_from_bytes(msg.key()), value=decode_from_bytes(msg.value()))

    def afficher_temperature(self, key, value):
        self.logger.info("{0}: Temperature: {1}".format(key, value))
        self.display.lcd_display_string("Temp: {temp} C".format(temp=value).ljust(16),
                                        self.ligne_temp)

    def afficher_niveau(self, key, value):
        self.logger.info("{0}: Niveau: {1} {2}".format(key, value['niveau'], value['message']))
        self.display.lcd_display_string("Niv: {niveau}".format(niveau=self.get_nom_niveau(value['niveau'])).ljust(16),
                                        self.ligne_niveau)

    def afficher_alerte(self, key, value):
        self.logger.warning("{0}: Alerte niveau: {1} {2}".format(key, value['niveau'], value['message']))
        self.display.lcd_display_string("Alerte: {niveau}".format(niveau=self.get_nom_niveau(value['niveau'])).ljust(16),
                                        self.ligne_alerte)

    def afficher_message_accueil(self):
        message_ligne_1 = "Console Sucrier".ljust(16)
        message_ligne_2 = "Attente msg...".ljust(16)
        self.logger.info(message_ligne_1 + ' ' + message_ligne_2)
        self.display.lcd_display_string(message_ligne_1, 1)
        self.display.lcd_display_string(message_ligne_2, 2)

    def get_nom_niveau(self, niveau):
        if niveau == 0:
            return "VIDE"
        if niveau == 1:
            return "MIN"
        if niveau == 2:
            return "BAS"
        if niveau == 3:
            return "NORMAL"
        if niveau == 4:
            return "HAUT"
        if niveau == 5:
            return "MAX"
        return "ERREUR"
    
sucrier = None

def signal_handler(sig, frame):
        GPIO.cleanup()
        sucrier.display.lcd_clear()
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument( '-log',
                        '--loglevel',
                        default='info',
                        help='Provide logging level. Example --loglevel debug, default=info' )

    args = parser.parse_args()
    sucrier = ConsoleSucrier(log_level=args.loglevel.upper())
    signal.signal(signal.SIGINT, signal_handler)
    consumer_thread = threading.Thread(target=sucrier.consommer_messages)
    consumer_thread.start()

if __name__ == "__main__":
    main()
