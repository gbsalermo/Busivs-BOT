"""Testes unitários da interpretação da rota principal.

Este arquivo documenta os comportamentos mínimos que ``src/rota.py`` deve
preservar: diferenciação da Biblioteca na ida/volta, mudança de sentido,
pontos opcionais, saltos válidos e rejeição de trechos inexistentes.
"""

import sys
import unittest
from pathlib import Path

# Os arquivos de produção ficam em ``src`` e o projeto ainda não está empacotado
# como módulo instalável. Por isso incluímos ``src`` no caminho de importação dos
# testes.
RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rota import analisar_trecho


class TestRotaPrincipal(unittest.TestCase):
    """Valida as transições importantes da rota do ônibus Principal."""

    def test_ida_pavilhao_1_para_biblioteca(self):
        """Biblioteca após Pavilhão I deve representar a ocorrência da ida."""
        resultado = analisar_trecho("pavilhao_1", "biblioteca")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RUA")
        self.assertEqual(resultado["proximo"]["id"], "pavilhao_2")

    def test_retorno_portao_1_para_biblioteca(self):
        """Biblioteca após Portão 1 deve representar a ocorrência da volta."""
        resultado = analisar_trecho("portao_1", "biblioteca")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RU")
        self.assertEqual(resultado["proximo"]["id"], "torre_cotec")
        self.assertTrue(resultado["proximo"]["opcional"])
        self.assertEqual(resultado["proximo"]["alternativa"]["id"], "ru")

    def test_canaa_para_portao_1_inicia_retorno(self):
        """Canãa -> Portão 1 deve indicar que o ônibus já retorna ao campus."""
        resultado = analisar_trecho("ponto_externo_2", "portao_1")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RU")
        self.assertEqual(resultado["proximo"]["id"], "biblioteca")

    def test_ponto_externo_1_para_canaa_ainda_indica_retorno_apos_canaa(self):
        """Ao chegar em Canãa, o próximo trecho esperado é o Portão 1."""
        resultado = analisar_trecho("ponto_externo_1", "ponto_externo_2")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RU")
        self.assertEqual(resultado["proximo"]["id"], "portao_1")

    def test_pula_pavilhao_engenharia_opcional(self):
        """Pavilhão II -> Portão 2 é válido quando Engenharia foi pulado."""
        resultado = analisar_trecho("pavilhao_2", "portao_2")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RUA")
        self.assertEqual(resultado["proximo"]["id"], "ponto_externo_1")

    def test_para_no_pavilhao_engenharia_opcional(self):
        """O ponto opcional também deve funcionar quando realmente atendido."""
        resultado = analisar_trecho("pavilhao_2", "pavilhao_engenharia")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RUA")
        self.assertEqual(resultado["proximo"]["id"], "portao_2")

    def test_pula_torre_cotec_opcional_no_retorno(self):
        """Biblioteca -> RU é válido quando Torre/COTEC não foi atendida."""
        resultado = analisar_trecho("biblioteca", "ru")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["sentido"], "RUA")

    def test_trecho_invalido_retorna_none(self):
        """Pontos conhecidos em ordem impossível não devem gerar inferência."""
        resultado = analisar_trecho("fitotecnia", "portao_1")
        self.assertIsNone(resultado)

    def test_ponto_inexistente_retorna_none(self):
        """IDs que não existem no cadastro devem ser rejeitados com segurança."""
        resultado = analisar_trecho("ponto_que_nao_existe", "biblioteca")
        self.assertIsNone(resultado)


# Permite executar isoladamente com ``python tests/test_rota.py``.
if __name__ == "__main__":
    unittest.main()
