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

from time import sleep

class ConsoleSucrier:
    topic_niveau = "bouillage.niveau"
    topic_alerte = "bouillage.alertes"
    topic_temp = "bouillage.temperature"
    logger = None
    consommateur = None
    ligne_niveau = 0
    ligne_temp = 1
    ligne_alerte = 2
    
    messages = ["Console Sucrier", "Attente msg...","Aucune alerte"]

    premiere_ligne = 0
    temps_rafraichissement_affichage = 10

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
                    self.lancer_alerte(key=decode_from_bytes(msg.key()), value=decode_from_bytes(msg.value()))

    def afficher_temperature(self, key, value):
        self.logger.info("{0}: Température: {1} C".format(key, value))
        self.messages[self.ligne_temp] = "Temp: {temp} C".format(temp=value)

    def afficher_niveau(self, key, value):
        self.logger.info("{0}: Niveau: {1} {2}".format(key, value['niveau'], value['message']))
        self.messages[self.ligne_niveau] = "Niveau: {niveau}".format(type=type,niveau=value['display'])

    def lancer_alerte(self, key, value):
        self.logger.warning("{0}: Alerte niveau: {1} {2}".format(key, value['niveau'], value['message']))
        self.messages[self.ligne_alerte] = "Alerte: {display}".format(display=value["display"])
        
    def rafraichir_affichage(self):
        while True:
            if self.premiere_ligne >= len(self.messages) - 1:
                self.premiere_ligne = 0
            self.logger.debug(self.messages[self.premiere_ligne])
            self.logger.debug(self.messages[self.premiere_ligne + 1])
            self.display.lcd_display_string(self.messages[self.premiere_ligne].ljust(16), 1)
            self.display.lcd_display_string(self.messages[self.premiere_ligne + 1].ljust(16), 2)
            self.premiere_ligne += 1
            sleep(self.temps_rafraichissement_affichage)
    
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
    display_thread = threading.Thread(target=sucrier.rafraichir_affichage)
    display_thread.start()

if __name__ == "__main__":
    main()
