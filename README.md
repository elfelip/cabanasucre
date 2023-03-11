# CabanASucre

Projet d'automatisation du bouillage de l'eau d'érable pour St-Red

# Composants

bouillage_ctrl_cmd
kafkabanansucre

## Kafkabanasucre

Pré-requis:
    Avoir un cluster Openshift ou OKD.
    L'opérateur Strimzi doit être déployé sur le cluster Openshift/OKD
    Les clients kubectl et oc doivent être installé sur le poste et ils doivent être configurés pour se brancher au cluster OKD avec des droits d'administrations.
    
Pour créer le cluster kafkabanasucre, suivre les étapes suivantes:

    Crééer le namespace:
        kubectl create namespace cabanasucre
    Attribuer le privilège anyuid au compte de service default du namespace cabanasucre:
        oc adm policy add-scc-to-user anyuid -z kafkabanasucre-zookeeper -n cabanasucre
        oc adm policy add-scc-to-user anyuid -z kafkabanasucre-kafka -n cabanasucre
    Appliquer le manifest pour créer le cluster kafka:
        oc apply -f kafka/kafkabanasucre-manifest.yaml
    Le cluster Kafka sera accessible par l'adresse suivante:
        kube06.lacave.info:31092,kube07.lacave.info:31093,kube08.lacave.info:31094
    On peut vérifier si les topics sont créés avec la commande suivante:
        docker run -ti --rm --name kafkatools --entrypoint kafka-topics confluentinc/cp-kafka:latest --bootstrap-server kube06.lacave.info:31092,kube07.lacave.info:31093,kube08.lacave.info:31094 --list
    On peut consommer les messages d'un topic avec la commande suivante:
        docker run -ti --rm --name kafkatools --entrypoint kafka-console-consumer confluentinc/cp-kafka:latest --bootstrap-server kube06.lacave.info:31092,kube07.lacave.info:31093,kube08.lacave.info:31094 --topic bouillage.niveau --from-beginning --property print.key=true

## bouillage_ctrl_cmd

Ce composant sert à mesurer la température du bouillage ainsi qu'à contrôler le niveau d'eau d'érable dans l'évaporateur.
Le contrôle de niveau d'eau se fait grâce à une sonde trempée dans l'évaporateur ainsi qu'un valve relié au réservoir d'eau d'érable.
Si le niveau d'eau tombe sous la sonde de niveau bas, la valve est ouverte et l'eau d'érable du réservoir est ajoutée dans l'évaporateur. Dès que l'eau d'érable atteint la sonde de niveau haut, la valve est alors fermée.
Si le niveau d'eau tombe sous la sonde de niveau minimum ou par dessus la sonde de niveau maximum, une alerte est envoyée.

Les mesures de niveau, de température ainsi que les alertes sont publiés sur le cluster Kafka afin d'être transmis au sucrier.

Il y a deux programme inclus dans ce conmposant:

    bouillage_controle.py: Controleur de bouillage principal
    console_sucrier.py: Console permettant d'accéder aux informations publiées par le controleur

### Controleur bouillage

On exécute ce composant sur le RaspberryPi Zero branché au circuit de CabanaSucre, la sonde de température, la sonde de niveau et la pompe du réservoir. Ce cicruit est relié au RaspberryPi Zero par son port GPIO.

Pré-requis
	Installer les packages suivants pour Kafka
	    sudo apt-get install librdkafka-dev
    Cloner le projet cabanasucre
        git clone https://github.com/elfelip/cabanasucre.git
	Installer les requirements.txt
        cd cabanasucre
	    python3 -m pip install -r requirements.txt

Définir la variable d'environnement pour la connexion a cluster Kafka en ajoutant la ligne suivante dans le fichier /home/pi/.bashrc:

    export BOOTSTRAP_SERVERS=kube06.lacave.info:31092,kube07.lacave.info:31093,kube08.lacave.info:31094

Pour automatiser le démarrage du programme sur le Rasbperry Pi Zéro, ajouter la ligne suivante dans le fichier /home/pi/.bashrc

    /home/pi/cabanasucre/start_cabanasucre.sh

Lancer l'interface de confiration raspi_config pour qu'une session pour l'utilisateur pi s'ouvre automatiquement au démarrage.

    sudo raspi-config
    Sélectionner 1 System Options -> S5 Boot / Auto login
    Sélectionner B2 Console Autologin Text console, automatically logged in as 'pi' user

Activer w1-temp toujours avec raspi-config:

    sudo raspi-config
    Sélectionner 3 Interface Options -> I7 1-Wire


## Console sucrier

Sur le Rasberry Pi3 on installe un affichage a cristaux liquide permettant de diffuser les différents messages emis pas le controleur.

Pré-requis
	Installer les packages suivants pour Kafka
	    sudo apt-get install librdkafka-dev
    Cloner le projet cabanasucre
        git clone https://github.com/elfelip/cabanasucre.git
	Installer les requirements.txt
        cd cabanasucre
	    python3 -m pip install -r requirements.txt
    Cloner le projet lcd suivant:
        mkdir the-rapberry-pi-guy
        cd the-rapsberry-pi-guy
        git clone https://github.com/the-raspberry-pi-guy/lcd.git
    Installer les pré-requis:
        cd lcd
        sudo ./install.sh


Pour configurer la connexion au cluster Kafka, définir la variable d'environnement BOOTSTRAP_SERVERS en ajoutant la ligne suivante dans le fichier /home/pi/.bashrc:

    export BOOTSTRAP_SERVERS=kube06.lacave.info:31092,kube07.lacave.info:31093,kube08.lacave.info:31094

Pour automatiser le démarrage du programme de console sur le Rasbperry Pi 3, ajouter la ligne suivante dans le fichier /home/pi/.bashrc

    /home/pi/cabanasucre/start_console.sh

Lancer l'interface de confiration raspi_config pour qu'une session pour l'utilisateur pi s'ouvre automatiquement au démarrage.

    sudo raspi-config
    Sélectionner 1 System Options -> S5 Boot / Auto login
    Sélectionner B2 Console Autologin Text console, automatically logged in as 'pi' user

### Développement

Pour pouvoir tester le code sur une autre plateforme que le Raspberry Pi, on doit installer les deux modules bidon suivants:

    fake_gpio:
        cd fake_gpio
        python3 -m pip install -U .
    fake_smbus:
        cd fake_smbus
        python3 -m pip install -U .
