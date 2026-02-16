from bouillage import NiveauCtrlCmd
import argparse
import signal
import sys
import threading
try:
    import RPi.GPIO as GPIO
except ImportError:
    import Mock.GPIO as GPIO

class FakeArgs():
    loglevel = "info"
    niveaubas = NiveauCtrlCmd.BAS
    niveauhaut = NiveauCtrlCmd.HAUT
    niveaumax = NiveauCtrlCmd.MAX
    logpath = "/tmp"
    logfile = "cabaneasucre.log"

parser = argparse.ArgumentParser(prog="bouillage_controle", description="Automatise le processus de bouillage de sirop d'érable")
parser.add_argument('-log',
                    '--loglevel',
                    default='info',
                    help='Provide logging level. Example --loglevel debug, default=info' )
parser.add_argument('-l',
                    '--niveaubas',
                    default=NiveauCtrlCmd.BAS,
                    type=int,
                    help='Niveau minimum pour le démarrage de la pompe. Example --niveaubas=3, défaut=2')
parser.add_argument('-u',
                    '--niveauhaut',
                    default=NiveauCtrlCmd.HAUT,
                    type=int,
                    help="Niveau a atteindre pour l'arrêt de la pompe. Example --niveauhaut=6, défaut=4")
parser.add_argument('-m',
                    '--niveaumax',
                    default=NiveauCtrlCmd.MAX,
                    type=int,
                    help="Niveau maximum possible. Example --niveaumax=8, défaut=8")
parser.add_argument('-p',
                    '--logpath',
                    default='/tmp',
                    type=str,
                    help='Répertoire du fichier de log. Example --logpath=/var/log, défaut=/tmp')
parser.add_argument('-f',
                    '--logfile',
                    default='cabanasucre',
                    type=str,
                    help='Nom du fichier de log. Example --logfile=cabane, défaut=cabanasucre')
try:
    args = parser.parse_args()
except:
    print("Erreur")
    args = FakeArgs()


ctrl_cmd = NiveauCtrlCmd(log_level=args.loglevel.upper(),
                         niveau_bas=args.niveaubas,
                         niveau_haut=args.niveauhaut,
                         niveau_max=args.niveaumax,
                         log_path=args.logpath,
                         log_file_name=args.logfile)

def signal_handler(sig, frame):
    ctrl_cmd.arreter_pompe()
    GPIO.cleanup()
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    temp_thread = threading.Thread(target=ctrl_cmd.lire_temperature)
    temp_thread.start()

if __name__ == "__main__":
    main()
