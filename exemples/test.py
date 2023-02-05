import signal
import sys
import threading
from time import sleep


class Test:
    VALEUR = 'test'
    def afficher(self):
        print(self.VALEUR)
        
    def demarrer(self):
        sleep(60)

le_test = Test()
       
def signal_handler(sig, frame):
    le_test.afficher()
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    temp_thread = threading.Thread(target=le_test.demarrer)
    temp_thread.start()
    #signal.pause()

if __name__ == "__main__":
    main()