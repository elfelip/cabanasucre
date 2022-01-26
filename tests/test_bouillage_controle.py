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
        
    def gpio_input_min_mock(*args, **kwargs):
        return False
    
    def gpio_input_bas_mock(*args, **kwargs):
        if args[0] == 5:
            return True
        return False
    
    def gpio_input_normal_mock(*args, **kwargs):
        if args[0] == 5 or args[0] == 17:
            return True
        return False

    def gpio_input_haut_mock(*args, **kwargs):
        if args[0] == 5 or args[0] == 17 or args[0] == 27:
            return True
        return False

    def gpio_input_max_mock(*args, **kwargs):
        return True

    def ouvrir_valve_mock(*args, **kwargs):
        valve = "ouverte"

    def fermer_valve_mock(*args, **kwargs):
        valve = "fermee"
        
    def lancer_alerte_max_mock(*args, **kwargs):
        pass
        
    def lancer_alerte_min_mock(*args, **kwargs):
        pass

    # Tests Sonde NIN_MIN
    @mock.patch('RPi.GPIO.setmode', side_effect=gpio_setmode_mock)
    @mock.patch('RPi.GPIO.setup', side_effect=gpio_setup_mock)
    @mock.patch('RPi.GPIO.add_event_detect', side_effect=gpio_add_event_detect_mock)
    @mock.patch('RPi.GPIO.input', side_effect=gpio_input_bas_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.ouvrir_valve', side_effect=ouvrir_valve_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.fermer_valve', side_effect=fermer_valve_mock)
    def test_etant_donne_niveau_min_si_la_sonde_de_niveau_min_est_touchee_par_l_eau_alors_le_niveau_est_bas(
        self,
        *mocks):

        controle_niveau = NiveauCtrlCmd()
        controle_niveau.NIVEAU = controle_niveau.MIN
        controle_niveau.traiter_event_detect_pour_sonde_niveau(controle_niveau.NIV_MIN_R)
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
                    "La metode ouvrir_valve auait du etre appele une fois a l'initialisation puisque le niveau initial est min."
                )
            if mock_name == "fermer_valve":
                self.assertEqual(
                    mock.call_count,
                    1,
                    "La metode fermer_valve aurait du etre appele une fois a l'initialisation du programme."
                )

    @mock.patch('RPi.GPIO.setmode', side_effect=gpio_setmode_mock)
    @mock.patch('RPi.GPIO.setup', side_effect=gpio_setup_mock)
    @mock.patch('RPi.GPIO.add_event_detect', side_effect=gpio_add_event_detect_mock)
    @mock.patch('RPi.GPIO.input', side_effect=gpio_input_min_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.ouvrir_valve', side_effect=ouvrir_valve_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.fermer_valve', side_effect=fermer_valve_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.lancer_alerte_min', side_effect=lancer_alerte_min_mock)
    def test_etant_donne_niveau_bas_si_la_sonde_min_n_est_plus_touchee_par_l_eau_alors_niveau_min_et_valve_ouverte_et_alerte_min(
        self,
        *mocks):
    
        controle_niveau = NiveauCtrlCmd()
        controle_niveau.NIVEAU = controle_niveau.BAS
        controle_niveau.traiter_event_detect_pour_sonde_niveau(controle_niveau.NIV_MIN_F)
        self.assertEqual(
            controle_niveau.NIVEAU,
            controle_niveau.MIN,
            "Niveau {0} incorrect. Devrait etre {1}".format(
                controle_niveau.NIVEAU,
                controle_niveau.MIN   
            )
        )
        for mock in mocks:
            mock_name = mock._extract_mock_name()
            if mock_name == "ouvrir_valve":
                self.assertEqual(
                    mock.call_count,
                    2,
                    "La metode ouvrir_valve aurait du etre appele 2 fois, une fois a l'initialisation puisque le niveu etait bas et une fois lors de la transition."
                )
            if mock_name == "fermer_valve":
                self.assertEqual(
                    mock.call_count,
                    1,
                    "La metode fermer_valve devrait avoir ete appele un fois lors de l'initialisation."
                )
            if mock_name == "lancer_alerte_min":
                self.assertEqual(
                    mock.call_count,
                    1,
                    "La methode lancer_alerte_min n'a pas ete appele malgre le niv sous min."
                )

    # Tests sonde NIV_BAS            
    @mock.patch('RPi.GPIO.setmode', side_effect=gpio_setmode_mock)
    @mock.patch('RPi.GPIO.setup', side_effect=gpio_setup_mock)
    @mock.patch('RPi.GPIO.add_event_detect', side_effect=gpio_add_event_detect_mock)
    @mock.patch('RPi.GPIO.input', side_effect=gpio_input_normal_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.ouvrir_valve', side_effect=ouvrir_valve_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.fermer_valve', side_effect=fermer_valve_mock)
    def test_etant_donne_niveau_bas_si_la_sonde_de_niveau_bas_est_touchee_par_l_eau_alors_le_niveau_est_normal(
        self,
        *mocks):

        controle_niveau = NiveauCtrlCmd()
        controle_niveau.NIVEAU = controle_niveau.BAS
        controle_niveau.traiter_event_detect_pour_sonde_niveau(controle_niveau.NIV_BAS_R)
        self.assertEqual(
            controle_niveau.NIVEAU,
            controle_niveau.NORMAL,
            "Niveau {0} incorrect. Devrait etre {1}".format(
                controle_niveau.NIVEAU,
                controle_niveau.NORMAL
            )
        )
        for mock in mocks:
            mock_name = mock._extract_mock_name()
            if mock_name == "ouvrir_valve":
                self.assertEqual(
                    mock.call_count,
                    0,
                    "La metode ouvrir_valve a ete appele. La valve n'aurais pas du etre ouverte."
                )
            if mock_name == "fermer_valve":
                self.assertEqual(
                    mock.call_count,
                    1,
                    "La metode fermer_valve aurait du etre appele une fois lors de l'initialisation."
                )

    @mock.patch('RPi.GPIO.setmode', side_effect=gpio_setmode_mock)
    @mock.patch('RPi.GPIO.setup', side_effect=gpio_setup_mock)
    @mock.patch('RPi.GPIO.add_event_detect', side_effect=gpio_add_event_detect_mock)
    @mock.patch('RPi.GPIO.input', side_effect=gpio_input_bas_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.ouvrir_valve', side_effect=ouvrir_valve_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.fermer_valve', side_effect=fermer_valve_mock)
    def test_etant_donne_niveau_normal_si_la_sonde_bas_n_est_plus_touchee_par_l_eau_alors_niveau_bas_et_valve_ouverte(
        self,
        *mocks):
    
        controle_niveau = NiveauCtrlCmd()
        controle_niveau.NIVEAU = controle_niveau.NORMAL
        controle_niveau.traiter_event_detect_pour_sonde_niveau(controle_niveau.NIV_BAS_F)
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
                    2,
                    "La metode ouvrir_valve aurait du etre appele 2 fois, une fois lors de l'initialisation pace que le niveau etait bas et une fois lrs de la transition."
                )
            if mock_name == "fermer_valve":
                self.assertEqual(
                    mock.call_count,
                    1,
                    "La metode fermer_valve aurait du etre appele une fois lors de l'initialisation."
                )

    # Tests sonde NIV_HAUT
    @mock.patch('RPi.GPIO.setmode', side_effect=gpio_setmode_mock)
    @mock.patch('RPi.GPIO.setup', side_effect=gpio_setup_mock)
    @mock.patch('RPi.GPIO.add_event_detect', side_effect=gpio_add_event_detect_mock)
    @mock.patch('RPi.GPIO.input', side_effect=gpio_input_haut_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.ouvrir_valve', side_effect=ouvrir_valve_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.fermer_valve', side_effect=fermer_valve_mock)
    def test_etant_donne_niveau_normal_si_la_sonde_de_niveau_haut_est_touchee_par_l_eau_alors_le_niveau_est_haut_et_fermer_valve(
        self,
        *mocks):

        controle_niveau = NiveauCtrlCmd()
        controle_niveau.NIVEAU = controle_niveau.NORMAL
        controle_niveau.traiter_event_detect_pour_sonde_niveau(controle_niveau.NIV_HAUT_R)
        self.assertEqual(
            controle_niveau.NIVEAU,
            controle_niveau.HAUT,
            "Niveau {0} incorrect. Devrait etre {1}".format(
                controle_niveau.NIVEAU,
                controle_niveau.HAUT
            )
        )
        for mock in mocks:
            mock_name = mock._extract_mock_name()
            if mock_name == "ouvrir_valve":
                self.assertEqual(
                    mock.call_count,
                    0,
                    "La metode ouvrir_valve a ete appele. La valve n'aurais pas du etre ouverte."
                )
            if mock_name == "fermer_valve":
                self.assertEqual(
                    mock.call_count,
                    2,
                    "La metode fermer_valve aurait du etre appele 2 fois, une fois a l'initialisation et une fois lors de la transition."
                )

    @mock.patch('RPi.GPIO.setmode', side_effect=gpio_setmode_mock)
    @mock.patch('RPi.GPIO.setup', side_effect=gpio_setup_mock)
    @mock.patch('RPi.GPIO.add_event_detect', side_effect=gpio_add_event_detect_mock)
    @mock.patch('RPi.GPIO.input', side_effect=gpio_input_normal_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.ouvrir_valve', side_effect=ouvrir_valve_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.fermer_valve', side_effect=fermer_valve_mock)
    def test_etant_donne_niveau_haut_si_la_sonde_haut_n_est_plus_touchee_par_l_eau_alors_niveau_normal(
        self,
        *mocks):
    
        controle_niveau = NiveauCtrlCmd()
        controle_niveau.NIVEAU = controle_niveau.HAUT
        controle_niveau.traiter_event_detect_pour_sonde_niveau(controle_niveau.NIV_HAUT_F)
        self.assertEqual(
            controle_niveau.NIVEAU,
            controle_niveau.NORMAL,
            "Niveau {0} incorrect. Devrait etre {1}".format(
                controle_niveau.NIVEAU,
                controle_niveau.NORMAL   
            )
        )
        for mock in mocks:
            mock_name = mock._extract_mock_name()
            if mock_name == "ouvrir_valve":
                self.assertEqual(
                    mock.call_count,
                    0,
                    "La metode ouvrir_valve a ete appele. La valve n'aurait pas du etre ouverte."
                )
            if mock_name == "fermer_valve":
                self.assertEqual(
                    mock.call_count,
                    1,
                    "La metode fermer_valve aurait du etre appele une fois lors de l'initialisation."
                )

    # Test sonde NIV_MAX
    @mock.patch('RPi.GPIO.setmode', side_effect=gpio_setmode_mock)
    @mock.patch('RPi.GPIO.setup', side_effect=gpio_setup_mock)
    @mock.patch('RPi.GPIO.add_event_detect', side_effect=gpio_add_event_detect_mock)
    @mock.patch('RPi.GPIO.input', side_effect=gpio_input_max_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.ouvrir_valve', side_effect=ouvrir_valve_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.fermer_valve', side_effect=fermer_valve_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.lancer_alerte_max', side_effect=lancer_alerte_max_mock)
    def test_etant_donne_niveau_haut_si_la_sonde_de_niveau_max_est_touchee_par_l_eau_alors_le_niveau_est_max_et_fermer_valve_et_alerte_niv_max(
        self,
        *mocks):

        controle_niveau = NiveauCtrlCmd()
        controle_niveau.NIVEAU = controle_niveau.HAUT
        controle_niveau.traiter_event_detect_pour_sonde_niveau(controle_niveau.NIV_MAX_R)
        self.assertEqual(
            controle_niveau.NIVEAU,
            controle_niveau.MAX,
            "Niveau {0} incorrect. Devrait etre {1}".format(
                controle_niveau.NIVEAU,
                controle_niveau.MAX
            )
        )
        for mock in mocks:
            mock_name = mock._extract_mock_name()
            if mock_name == "ouvrir_valve":
                self.assertEqual(
                    mock.call_count,
                    0,
                    "La metode ouvrir_valve a ete appele. La valve n'aurais pas du etre ouverte."
                )
            if mock_name == "fermer_valve":
                self.assertEqual(
                    mock.call_count,
                    2,
                    "La metode fermer_valve aurait du etre appele 2 fois, une fois a l'initialisation et une fois lors de la transition."
                )
            if mock_name == "lancer_alerte_max":
                self.assertEqual(
                    mock.call_count,
                    1,
                    "La methode lancer_alerte_max n'a pas ete appele malgre le niv max atteint."
                )

    @mock.patch('RPi.GPIO.setmode', side_effect=gpio_setmode_mock)
    @mock.patch('RPi.GPIO.setup', side_effect=gpio_setup_mock)
    @mock.patch('RPi.GPIO.add_event_detect', side_effect=gpio_add_event_detect_mock)
    @mock.patch('RPi.GPIO.input', side_effect=gpio_input_haut_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.ouvrir_valve', side_effect=ouvrir_valve_mock)
    @mock.patch('bouillage_ctrl_cmd.bouillage_controle.NiveauCtrlCmd.fermer_valve', side_effect=fermer_valve_mock)
    def test_etant_donne_niveau_max_si_la_sonde_max_n_est_plus_touchee_par_l_eau_alors_niveau_haut(
        self,
        *mocks):
    
        controle_niveau = NiveauCtrlCmd()
        controle_niveau.NIVEAU = controle_niveau.MAX
        controle_niveau.traiter_event_detect_pour_sonde_niveau(controle_niveau.NIV_MAX_F)
        self.assertEqual(
            controle_niveau.NIVEAU,
            controle_niveau.HAUT,
            "Niveau {0} incorrect. Devrait etre {1}".format(
                controle_niveau.NIVEAU,
                controle_niveau.HAUT   
            )
        )
        for mock in mocks:
            mock_name = mock._extract_mock_name()
            if mock_name == "ouvrir_valve":
                self.assertEqual(
                    mock.call_count,
                    0,
                    "La metode ouvrir_valve a ete appele. La valve n'aurait pas du etre ouverte."
                )
            if mock_name == "fermer_valve":
                self.assertEqual(
                    mock.call_count,
                    1,
                    "La metode fermer_valve aurait du etre appele une fois lors de l'initialisation."
                )
                
    
if __name__ == '__main__':
    unittest.main()
