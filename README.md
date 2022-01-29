# CabanASucre

Projet d'automatisation du bouillage de l'eau d'érable pour St-Red

# Composants

bouillage_ctrl_cmd
sucrier
kafkabanansucre

## bouillage_ctrl_cmd

Ce composant sert à mesurer la température du bouillage ainsi qu'à contrôler le niveau d'eau d'érable dans l'évaporateur.
Le contrôle de niveau d'eau se fait grâce à une sonde trempée dans l'évaporateur ainsi qu'un valve relié au réservoir d'eau d'érable.
Si le niveau d'eau tombe sous la sonde de niveau bas, la valve est ouverte et l'eau d'érable du réservoir est ajoutée dans l'évaporateur. Dès que l'eau d'érable atteint la sonde de niveau haut, la valve est alors fermée.
Si le niveau d'eau tombe sous la sonde de niveau minimum ou par dessus la sonde de niveau maximum, une alerte est envoyée.

Les mesures de niveau, de température ainsi que les alertes sont publiés sur le cluster Kafka afin d'être transmis au sucrier.

On exécute ce composant sur le RaspberryPi Zero sur lequel est branché le circuit de CabanaSucre, la sonde de température, la sonde de niveau et la valve du réservoir. Ce cicruit est relié au RaspberryPi Zero par son port GPIO.

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
