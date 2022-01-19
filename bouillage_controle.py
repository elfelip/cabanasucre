#!/usr/bin/env python3

import signal
import sys
import RPi.GPIO as GPIO

NIV_BAS_ALERTE = 7
NIV_BAS = 11
NIV_MAX = 13
NIV_MAX_ALERTE = 15

def signal_handler(sig, frame):
    GPIO.cleanup()
    sys.exit(0)

def lancer_alerte_vide():
    print("Alerte, Le chaudron est vide.")

def lancer_alerte_bas():
    print("Alerte: niveau trop bas, le réservoir est probablement vide")
    
def ouvrir_valve():
    print("Niveau minimal atteint, ouvrir la valve pour ajouter de l'eau.")
    
def fermer_valve():
    print("Le niveau maximum est atteint, fermer le valve.")
    
def lancer_alerte_max():
    print("Alerte, le niveau d'eau est trop haut. Il y a probablement un problème avec la valve.")    

def lancer_erreur_niveau():
    print("Les informations de niveau sont incohérents, il doit y avoir un problème avec la sonde.")

def traiter_inputs_callback(channel):
    print("Channel: {0}".format(channel))
    if ((GPIO.input(NIV_BAS_ALERTE) and not 
        (GPIO.input(NIV_BAS) or GPIO.input(NIV_MAX) or GPIO.input(NIV_MAX_ALERTE)))):
        lancer_alerte_bas()
    elif ((GPIO.input(NIV_BAS_ALERTE) and GPIO.input(NIV_BAS)) and not
        (GPIO.input(NIV_MAX) or GPIO.input(NIV_MAX_ALERTE))):
        ouvrir_valve()
    elif ((GPIO.input(NIV_BAS_ALERTE) and GPIO.input(NIV_BAS) and GPIO.input(NIV_MAX)) and not
        GPIO.input(NIV_MAX_ALERTE)):
        fermer_valve()
    elif (GPIO.input(NIV_BAS_ALERTE) and GPIO.input(NIV_BAS) and GPIO.input(NIV_MAX)) and GPIO.input(NIV_MAX_ALERTE):
        lancer_alerte_max()
    elif not (GPIO.input(NIV_BAS_ALERTE) or GPIO.input(NIV_BAS) or GPIO.input(NIV_MAX) or GPIO.input(NIV_MAX_ALERTE)):
        lancer_alerte_vide()
    else:
        lancer_erreur_niveau()

def main():
    GPIO.setmode(GPIO.BCM)
    
    connecteurs = [NIV_BAS_ALERTE, NIV_BAS, NIV_MAX, NIV_MAX_ALERTE]

    for connecteur in connecteurs:
        GPIO.setup(connecteur, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(connecteur, GPIO.RISING, callback=traiter_inputs_callback, bouncetime=200)

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()
            

if __name__ == "__main__":
    main()