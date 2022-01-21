#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bouillage_controle import NiveauCtrlCmd
import unittest
from unittest import TestCase #, mock

#def gpio_setmode_mock(mode):
#    pass

#def gpio_setup_mock(connecteur, mode, pull_up_down):
#    pass

#def gpio_add_event_detect_mock(connecteur, mode, callback, bouncetime):
#    pass

class TestNiveauCtrlCmd(TestCase):
    #@mock.patch('bouillage_controle.NiveauCtrlCmd.GPIO.setmode', side_effect=gpio_setmode_mock)
    #@mock.patch('bouillage_controle.NiveauCtrlCmd.GPIO.setup', side_effect=gpio_setup_mock)
    #@mock.patch('bouillage_controle.NiveauCtrlCmd.GPIO.add_event_detect', side_effect=gpio_add_event_detect_mock)
    #def test_etant_donne_le_niveau_vide_si_la_sonde_de_niveau_bas_est_touchee_par_l_eau_alors_le_niveau_est_bas(
    #    self,
    #    gpio_setmode_mock,
    #    gpio_setup_mock,
    #    gpio_add_event_detect_mode):
    def test_etant_donne_le_niveau_vide_si_la_sonde_de_niveau_bas_est_touchee_par_l_eau_alors_le_niveau_est_bas(self):
        controle_niveau = NiveauCtrlCmd()
        controle_niveau.traiter_gpio_up_pour_sonde_min(controle_niveau.NIV_MIN)
        self.assertEqual(
            controle_niveau.NIVEAU,
            controle_niveau.BAS,
            "Niveau {0} incorrect. Devrait etre {1}".format(
                controle_niveau.NIVEAU,
                controle_niveau.BAS
            )
        )
    
if __name__ == '__main__':
    unittest.main()
