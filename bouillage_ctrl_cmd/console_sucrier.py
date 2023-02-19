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

class ConsoleSucrier:
    topic_niveau = "bouillage.niveau"
    topic_alerte = "bouillage.alertes"
    topic_temp = "bouillage.temperature"

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        self.kafka_config = obtenirConfigurationsConsommateurDepuisVariablesEnvironnement(logger=logging) if 'BOOTSTRAP_SERVERS' in os.environ else None
        liste_topics = [self.topic_alerte, self.topic_niveau, self.topic_temp]
        self.consommateur = creerConsommateur(config=self.kafka_config.kafka, topics=liste_topics) if self.kafka_config is not None else None

    def consommer_messages(self):
        if self.consommateur is None:
            return
        while True:
            msg = self.consommateur.poll(timeout=0.1)
            if msg is not None:
                if msg.error():
                    logging.error("Erreur Kafka: {0} {1}".format(msg.error().code(), msg.error().str()))
                if msg.topic() == self.topic_temp:
                    self.afficher_temperature(key=decode_from_bytes(msg.key()), value=decode_from_bytes(msg.value()))
                elif msg.topic() == self.topic_niveau:
                    self.afficher_niveau(key=decode_from_bytes(msg.key()), value=decode_from_bytes(msg.value()))
                elif msg.topic() == self.topic_alerte:
                    self.afficher_alerte(key=decode_from_bytes(msg.key()), value=decode_from_bytes(msg.value()))

    def afficher_temperature(self, key, value):
        logging.info("{0}: Temperature: {1}".format(key, value))

    def afficher_niveau(self, key, value):
        logging.info("{0}: Niveau: {1} {2}".format(key, value['niveau'], value['message']))

    def afficher_alerte(self, key, value):
        logging.warning("{0}: Niveau: {1} {2}".format(key, value['niveau'], value['message']))
    
def signal_handler(sig, frame):
        GPIO.cleanup()
        sys.exit(0)

def main():
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(
        format=format,
        level=logging.INFO,
        datefmt="%H:%M:%S")

    sucrier = ConsoleSucrier()
    signal.signal(signal.SIGINT, signal_handler)
    consumer_thread = threading.Thread(target=sucrier.consommer_messages)
    consumer_thread.start()
    #signal.pause()

if __name__ == "__main__":
    main()
