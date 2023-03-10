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

class ConsoleSucrier:
    topic_niveau = "bouillage.niveau"
    topic_alerte = "bouillage.alertes"
    topic_temp = "bouillage.temperature"
    logger = None
    consommateur = None
    ligne_niveau = 1
    ligne_temp = 2
    ligne_alerte = 1

    def __init__(self):
        format = "%(asctime)s: %(message)s"
        logging.basicConfig(
            format=format,
            level=logging.INFO,
            encoding='utf-8',
            datefmt="%H:%M:%S")
        self.logger=logging.getLogger('console_sucrier')
        self.logger.setLevel(logging.INFO)
        #console_handler = logging.StreamHandler()
        #console_formatter = logging.Formatter(format)
        #console_handler.setLevel(logging.INFO)
        #console_handler.setFormatter(console_formatter)
        #self.logger.addHandler(console_handler)

        GPIO.setmode(GPIO.BCM)
        self.kafka_config = obtenirConfigurationsConsommateurDepuisVariablesEnvironnement(logger=self.logger) if 'BOOTSTRAP_SERVERS' in os.environ else None
        if self.kafka_config is not None:
            self.kafka_config.kafka['auto.offset.reset'] = OFFSET_END
            liste_topics = [self.topic_alerte, self.topic_niveau, self.topic_temp]
            #self.consommateur = creerConsommateur(config=self.kafka_config.kafka, topics=liste_topics) if self.kafka_config is not None else None
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
        self.display.lcd_display_string("Temp: {temp} °C".format(temp=value), self.ligne_temp)

    def afficher_niveau(self, key, value):
        self.logger.info("{0}: Niveau: {1} {2}".format(key, value['niveau'], value['message']))
        self.display.lcd_display_string("Niv: {niveau}".format(niveau=value['niveau']), self.ligne_niveau)

    def afficher_alerte(self, key, value):
        self.logger.warning("{0}: Alerte niveau: {1} {2}".format(key, value['niveau'], value['message']))
        self.display.lcd_display_string("Alerte: {niveau}".format(niveau=value['niveau']), self.ligne_alerte)


    def afficher_message_accueil(self):
        message_ligne_1 = "Console Sucrier"
        message_ligne_2 = "Attente controleur"
        self.logger.info(message_ligne_1 + ' ' + message_ligne_2)
        self.display.lcd_display_string(message_ligne_1, 1)
        self.display.lcd_display_string(message_ligne_2, 2)
    
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
