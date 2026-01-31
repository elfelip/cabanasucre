#!/usr/bin/env python3
# -*- coding: utf-8 -*-

try:
    import RPi.GPIO as GPIO
except ImportError:
    import Mock.GPIO as GPIO
import logging
import os
from inspqkafka.consommateur import obtenirConfigurationsConsommateurDepuisVariablesEnvironnement, decode_from_bytes
from confluent_kafka import OFFSET_END, Consumer
import drivers

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
    temperature = None
    date_heure_derniere_temperature = None
    niveau = None
    date_heure_dernier_niveau = None
    alerte = None
    date_heure_derniere_alerte = None

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

    def afficher_temperature(self, key: str, value: str):
        self.logger.info("{0}: Température: {1} C".format(key, value))
        self.temperature = value
        self.date_heure_derniere_temperature = key
        self.messages[self.ligne_temp] = "Temp: {temp} C".format(temp=self.temperature)

    def afficher_niveau(self, key: str, value: dict[str]):
        self.logger.info("{0}: Niveau: {1} {2}".format(key, value['niveau'], value['message']))
        self.niveau = value
        self.date_heure_dernier_niveau = key
        self.messages[self.ligne_niveau] = "Niveau: {niveau}".format(type=type,niveau=value['display'])

    def lancer_alerte(self, key: str, value: dict[str]):
        self.logger.warning("{0}: Alerte niveau: {1} {2}".format(key, value['niveau'], value['message']))
        self.alerte = value
        self.date_heure_derniere_alerte = key
        self.messages[self.ligne_alerte] = "{display}".format(display=value["display"])
        
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
    
