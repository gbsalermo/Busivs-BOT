import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rota import analisar_trecho


class TestRotaPrincipal(unittest.TestCase):
    def test_ida_pavilhao_1_para_biblioteca(self):
        resultado = analisar_trecho("pavilhao_1", "biblioteca")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RUA")
        self.assertEqual(resultado["proximo"]["id"], "pavilhao_2")

    def test_retorno_portao_1_para_biblioteca(self):
        resultado = analisar_trecho("portao_1", "biblioteca")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RU")
        self.assertEqual(resultado["proximo"]["id"], "torre_cotec")
        self.assertTrue(resultado["proximo"]["opcional"])
        self.assertEqual(resultado["proximo"]["alternativa"]["id"], "ru")

    def test_canaa_para_portao_1_inicia_retorno(self):
        resultado = analisar_trecho("ponto_externo_2", "portao_1")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RU")
        self.assertEqual(resultado["proximo"]["id"], "biblioteca")

    def test_ponto_externo_1_para_canaa_ainda_indica_retorno_apos_canaa(self):
        resultado = analisar_trecho("ponto_externo_1", "ponto_externo_2")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RU")
        self.assertEqual(resultado["proximo"]["id"], "portao_1")

    def test_pula_pavilhao_engenharia_opcional(self):
        resultado = analisar_trecho("pavilhao_2", "portao_2")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RUA")
        self.assertEqual(resultado["proximo"]["id"], "ponto_externo_1")

    def test_para_no_pavilhao_engenharia_opcional(self):
        resultado = analisar_trecho("pavilhao_2", "pavilhao_engenharia")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RUA")
        self.assertEqual(resultado["proximo"]["id"], "portao_2")

    def test_pula_torre_cotec_opcional_no_retorno(self):
        resultado = analisar_trecho("biblioteca", "ru")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RUA")

    def test_trecho_invalido_retorna_none(self):
        resultado = analisar_trecho("fitotecnia", "portao_1")
        self.assertIsNone(resultado)

    def test_ponto_inexistente_retorna_none(self):
        resultado = analisar_trecho("ponto_que_nao_existe", "biblioteca")
        self.assertIsNone(resultado)


if __name__ == "__main__":
    unittest.main()
