from console import ConsoleSucrier
import signal
import sys
try:
    import RPi.GPIO as GPIO
except ImportError:
    import Mock.GPIO as GPIO
import threading
import argparse

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
