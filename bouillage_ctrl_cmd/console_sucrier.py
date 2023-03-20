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
    dernieres_temperatures = []
    nb_mesures_temp_pour_calcule_base = 3
    ecart_pour_fin_bouillage = 3
    temperature_base = None
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
                    self.traiter_temperature(key=decode_from_bytes(msg.key()), value=decode_from_bytes(msg.value()))
                elif msg.topic() == self.topic_niveau:
                    self.afficher_niveau(key=decode_from_bytes(msg.key()), value=decode_from_bytes(msg.value()))
                elif msg.topic() == self.topic_alerte:
                    self.lancer_alerte(key=decode_from_bytes(msg.key()), value=decode_from_bytes(msg.value()))

    def traiter_temperature(self, key, value):
        self.logger.info("{0}: Temperature: {1}".format(key, value))
        self.messages[self.ligne_temp] = "Temp: {temp} C".format(temp=value)
        if self.temperature_base is None:
            self.calculer_temperature_base(temp=value)
        elif value > self.temperature_base + self.ecart_pour_fin_bouillage:
            self.logger.warning("La temperature de bouillage est atteinte {temp}".format(temp=value))
            self.messages[self.ligne_alerte] = "Fin boil {temp}".format(temp=value)
        elif value < self.temperature_base - 0.5:
            self.logger.warning("La temperature est sous la temperature de base {temp}".format(temp=value))
            self.messages[self.ligne_alerte] = "Tmp basse {temp}".format(temp=value)

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
        self.messages[self.ligne_niveau] = "{niveau}".format(type=type,niveau=value['display'])

    def lancer_alerte(self, key, value):
        self.logger.warning("{0}: Alerte niveau: {1} {2}".format(key, value['niveau'], value['message']))
        self.messages[self.ligne_alerte] = "Alerte: {display}".format(value["niveau"])
        
    def rafraichir_affichage(self):
        while True:
            if self.premiere_ligne >= len(self.messages - 2):
                self.premiere_ligne = 0
            
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
