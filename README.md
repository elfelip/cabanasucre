# CabanASucre

Projet d'automatisation du bouillage de l'eau d'érable pour St-Red

# Le procédé

Le bouillage de l'eau d'érable, dans ce projet, se fait dans un chaudron à blé d'inde et un bruleur au propane. 
L'eau d'érable récolté est versé dans une tonneau.
Une pompe 12 volt permet de transférer l'eau du tonneau vers le le chaudron à blé d'inde.
Le système permet de garder un certain niveau dans le chaudron lors du bouillage afin d'optimiser l'évaporation de l'eau et la consommation de gaz.
Les niveaux haut et bas entre lesquels l'eau est maintenu est configurable. La différence entre les niveaux de la sonde est d'à peu près un pouce.
Par exemple, si le niveau bas est 2 et le niveau haut est 3, le niveau d'eau maintenu pas le système sera entre 2 et 3 pouces du fond du chaudron.
La sonde possède 8 niveau. Le niveau minimum est donc de 1 pouce et le niveau maximum est de 8 pouces. Si le niveau d'eau descend sous le niveau minimum, une alerte est lancé et le bouillage devra être arrêté. Si le niveau monte au delà de 8 pouces, la pompe sera arrêté si elle est en fonction et une alerte sera lancé.

Ce procédé est utilisé pour faire une première réduction de l'eau d'érable pour en produire ce qu'on appelle du réduit. Rendu à cette étape, on peut décider de prendre le réduit avec du Gin. C'est bon pour un verre ou deux mais apès, l'idéal c'est d'en faire du sirop d'érable.

Pour la finition, le réduit est transféré dans un chaudron qui est chauffé sur une cuisinière électrique.
Les sondes de niveau et de température sont installées dans le chaudron et le système de contrôle est relancé.
Un processus de détection de la température de base pour le bouillage est initié. Le but est de détecter la température d'ébulition de l'eau qui varie avec la pression athmosphérique. Dès que la température s'est stabilisé, elle est mise en mémoire. Une alerte sera lancé quand le température sera de 4 degrés celcius de plus que la valeur de base mesuré. Le sirop d'érable est alors prêt.

# Composants

Voici les composants de ce projet:

    bouillage_ctrl_cmd: Composant controlant le processus et affichant les informations.
        bouillage_controle: Contrôle la pompe, mesure la température et diffuse les informations sur le procédé.
        console_sucrier: Affiche les informations et les messages du processus.
    kafkabanansucre: Courtier de messagerie permettant la communication entre le contrôleur et la console.

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

Le projet peut fonctionner avec un cluster Kafka à un noeud sur Docker. Je vais éventuellement ajouter un fichier docker-compose mais il y a plein d'exemple dans la documentation de Kafka.

## bouillage_ctrl_cmd

Ce composant sert à mesurer la température du bouillage ainsi qu'à contrôler le niveau d'eau d'érable dans le chaudron.
Le contrôle de niveau d'eau se fait grâce à une sonde trempée dans l'évaporateur ainsi qu'une pompe et des tuyaux reliants le réservoir d'eau d'érable et le chaudron.
Si le niveau d'eau tombe sous la sonde de niveau bas, la pompe est démarrée et l'eau d'érable du réservoir est ajoutée dans le chaudron. Dès que l'eau d'érable atteint la sonde de niveau haut, la pompe est alors arrêtée.
Si le niveau d'eau tombe sous la sonde de niveau minimum ou par dessus la sonde de niveau maximum, une alerte est envoyée.

Les mesures de niveau, de température ainsi que les alertes sont publiés sur le cluster Kafka afin d'être transmises au sucrier.

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


### Sonde de niveau

La sonde de niveau est constitué de 9 fils d'acier incoxydable recouvert de plastique. Ces fils sont dévouverts de leur gaine à leur base sur à peu près 3 mm pour permettre le contact électrique. Le premier fil se rend presque au fond du chaudron. Le deuxième fil est placé à un pouce du fond, le troisième à 2 pouces du fond ainsi de suite jusqu'au niveau maximum de 8 pouces.

### Sonde de température.

La sone de température est un sonde DS8. Elle est relié au Raspberry py 0 par l'interface 1-wire.

### Console sucrier

Sur le Rasberry Pi3 on installe un affichage a cristaux liquide permettant de diffuser les différents messages emis pas le controleur.

Pré-requis
	Installer les packages suivants pour Kafka
	    sudo apt-get install librdkafka-dev
    Cloner le projet cabanasucre
        git clone https://github.com/elfelip/cabanasucre.git
	Installer les requirements.txt
        cd cabanasucre
	    python3 -m pip install -r requirements.txt


Pour configurer la connexion au cluster Kafka, définir la variable d'environnement BOOTSTRAP_SERVERS en ajoutant la ligne suivante dans le fichier /home/pi/.bashrc:

    export BOOTSTRAP_SERVERS=kube06.lacave.info:31092,kube07.lacave.info:31093,kube08.lacave.info:31094

Pour automatiser le démarrage du programme de console sur le Rasbperry Pi 3, ajouter la ligne suivante dans le fichier /home/pi/.bashrc

    /home/pi/cabanasucre/start_console.sh

Lancer l'interface de confiration raspi_config pour qu'une session pour l'utilisateur pi s'ouvre automatiquement au démarrage.

    sudo raspi-config
    Sélectionner 1 System Options -> S5 Boot / Auto login
    Sélectionner B2 Console Autologin Text console, automatically logged in as 'pi' user
    Sélectionner 3 Interface Options
    Sélectionner I5 I2C Enable/Disable automatic loading of I2C kernel module. Répondre Yes
    Finish
    Reboot now Yes

# Équipement nécessaires
Voici la liste des éléments nécessaires pour ce projet avec des références Amazon:

    Unité de calcules:
        2 Raspberry pi avec cartes Wifi. Pour mon système, j'ai un Raspberry PI Zero pour le contrôleur et un Rasberry PI 3 pour la console. Raspberry PI Zero 2W avec têtes pré-soudées (40$). Raspberry PI 4 Modèle B (88$)
        Un réseau sans fil.
        Un serveur Kafka
    Alimentation électrique:
        Une batterie 12v pour alimenter la pompe et le Raspberry PI du contrôleur. Batterie a décharge profonde 12 V 14 AH (67$).
        Un panneau solaire 12v sur la cabane à sucre pour recharger la batterie. POWOXI chargeur de batterie solaire 7.5W 12 V (50$) 
        Un branchement allume cigare et un adaptateur USB allume cigare pour alimenter le Raspberry PI avec la batterie 12 volts. HATMINI Lot de 3 prises allume-cigare femelle 18 AWG avec câble à extrémité ouverte 12/24V pour équipement de moins de 120W (14$).
    Mécanique:
        Une pompe a eau de VR 12 volts. SAILFLO Pompe à eau 12 V CC à diaphragme à amorcage automatique et interrupteur de pression (36$).
    Circuit électronique:
        Une plaque de cicuit électrique pour les divers connexions avec le Raspberry pi. Electronics-Salon D-1228 (7$)
        Un affichage LED 2 par 20. FREENOVE I2C Lot de 2 modules LCD 1602 compatibles avec Arduino et Raspberry PI LCD1602 (17$). 
        Une sonde de température. Micreen lot de 2 modules capteur de température DS18B20 avec sonde étanche en acier inoxydable avec puce pour Arduino et Raspberry PI (14$)
        Résistance de 220 ohms
        Un fil 20 broches et un connecteur pour relier le circuit électronique avec le Raspberry pi. Pour les vieux de la vieille, un fil de disque dur IDE.
    Sondes (température et niveau):
        Une prise jack 1/8 stéréo femelle. Longdex lot de 3 connecteurs jack stéréo 3,5mm (15$)
        Une prise jack 1/8 stéréo mâle.
        Un fil 4 brins habituellement utilisé pour les thermostats de maison.
        Une prise DB9 mâle avec connecteur (anciennement utilisé pour relier les ports séries aux motherboards).
        Une prise DB9 femelle avec fil 9 brins en cuivre à extrémité ouvert (anciennement utilisé pour les modems externes)
        Du fil en acier inoxydable avec gaine en plastique. Au moins 20 pieds.
        Idéalement un abri pour éviter d'endomager le système lors du bouillage à l'extérieur. Un jeux extérieur d'enfant converti en cabane est l'idéal.
    
# Développement

Pour pouvoir tester le code sur une autre plateforme que le Raspberry Pi, on doit installer les deux modules bidon suivants:

    fake_gpio:
        cd fake_gpio
        python3 -m pip install -U .
    fake_smbus:
        cd fake_smbus
        python3 -m pip install -U .
