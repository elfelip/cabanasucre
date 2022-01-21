#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bouillage_ctrl_cmd.bouillage_controle import NiveauCtrlCmd
import unittest
from unittest import TestCase, mock

class TestNiveauCtrlCmd(TestCase):
    def setUp(self) -> None:
        self.callbacks = []
        return super().setUp()
    def gpio_setmode_mock(*args, **kwargs):
        pass

    def gpio_setup_mock(*args, **kwargs):
        pass

    def gpio_add_event_detect_mock(*args, **kwargs):
        callback = kwargs['callback'].__name__
        
    def gpio_input_mock(*args, **kwargs):
        pass
    
    def ouvrir_valve_mock(*args, **kwargs):
        valve = "ouverte"

    def fermer_valve_mock(*args, **kwargs):
        valve = "fermee"

    @mock.patch('RPi.GPIO.setmode', side_effect=gpio_setmode_mock)
    @mock.patch('RPi.GPIO.setup', side_effect=gpio_setup_mock)
    @mock.patch('RPi.GPIO.add_event_detect', side_effect=gpio_add_event_detect_mock)
    def test_etant_donne_le_niveau_vide_si_la_sonde_de_niveau_bas_est_touchee_par_l_eau_alors_le_niveau_est_bas(
        self,
        *mocks):

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
    @mock.patch('RPi.GPIO.setmode', side_effect=gpio_setmode_mock)
    @mock.patch('RPi.GPIO.setup', side_effect=gpio_setup_mock)
    @mock.patch('RPi.GPIO.add_event_detect', side_effect=gpio_add_event_detect_mock)
    @mock.patch('RPi.GPIO.input', side_effect=gpio_input_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.ouvrir_valve', side_effect=ouvrir_valve_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.fermer_valve', side_effect=fermer_valve_mock)
    def test_etant_donne_niveau_normal_si_la_sonde_bas_n_est_plus_touchee_par_l_eau_alors_niveau_bas_et_valve_ouverte(
        self,
        *mocks):
    
        controle_niveau = NiveauCtrlCmd()
        controle_niveau.NIVEAU = NiveauCtrlCmd.NORMAL
        controle_niveau.traiter_gpio_down_pour_sonde_bas(controle_niveau.NIV_BAS)
        self.assertEqual(
            controle_niveau.NIVEAU,
            controle_niveau.BAS,
            "Niveau {0} incorrect. Devrait etre {1}".format(
                controle_niveau.NIVEAU,
                controle_niveau.BAS   
            )
        )
        for mock in mocks:
            mock_name = mock._extract_mock_name()
            if mock_name == "ouvrir_valve":
                self.assertEqual(
                    mock.call_count,
                    1,
                    "La metode ouvrir_valve n'a pas ete appele. La valve n'a pas ete ouverte."
                )
            if mock_name == "fermer_valve":
                self.assertEqual(
                    mock.call_count,
                    0,
                    "La metode fermer_valve a ete appele. La valve n'aurais pas du etre ferme."
                )

if __name__ == '__main__':
    unittest.main()
