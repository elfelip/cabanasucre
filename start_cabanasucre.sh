echo Attendre 30 secondes avant de demarrer Cabanasucre
sleep 30
echo Demarrage Cabanasucre
python3 /home/pi/cabanasucre/bouillage_ctrl_cmd/bouillage_controle.py > /var/log/cabanasucre.log 2> /var/log/cabanasucre.err