"""Testes da correção colaborativa das confirmações de passagem.

Esses cenários garantem que uma informação errada não congele o bot. O sistema
mantém um histórico curto e procura a confirmação anterior mais recente que
forme uma sequência válida com o ponto novo.
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path

# Inclui ``src`` no caminho de importação para testar os módulos do projeto sem
# exigir instalação como pacote Python.
RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import passagens


class TestConfirmacoesColaborativas(unittest.TestCase):
    """Valida resiliência a registros errados e limite do histórico em memória."""

    def setUp(self):
        """Garante isolamento entre os cenários."""
        passagens.limpar_estado()

    def _hora(self, hora: int, minuto: int) -> datetime:
        """Cria horários de teste sempre no mesmo dia e fuso local."""
        return datetime(2026, 8, 10, hora, minuto, tzinfo=passagens.FUSO_LOCAL)

    def test_registro_errado_incompativel_nao_bloqueia_sequencia_correta(self):
        """Um registro incompatível mais recente pode ser ignorado em favor de outro válido."""
        # Fitotecnia é compatível com Pavilhão I; Portão 1, inserido depois,
        # representa ruído e não deve impedir a inferência correta.
        passagens._registrar_no_historico("fitotecnia", self._hora(12, 0), 101)
        passagens._registrar_no_historico("portao_1", self._hora(12, 5), 102)

        resultado = passagens._resultado_com_historico("pavilhao_1")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["ponto_anterior"], "Fitotecnia")
        self.assertEqual(resultado["ponto_atual"], "Pavilhão de Aulas I")
        self.assertTrue(resultado["ignorou_registro_incompativel"])

    def test_ru_errado_seguido_de_alex_nao_impede_alex_de_ser_usado(self):
        """Uma confirmação anterior no RU não impede Alex de virar o ponto atual útil."""
        passagens._registrar_no_historico("ru", self._hora(12, 12), 201)

        resultado = passagens._resultado_com_historico("ponto_externo_1")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["ponto_atual"], "Ponto Externo I / Alex")
        self.assertEqual(resultado["sentido"], "RUA")
        self.assertEqual(resultado["proximo"]["id"], "ponto_externo_2")

    def test_confirmacao_seguinte_reforca_sequencia_alex_canaa(self):
        """Alex seguido de Canãa deve formar uma sequência direta e consistente."""
        passagens._registrar_no_historico("ru", self._hora(12, 12), 201)
        passagens._registrar_no_historico("ponto_externo_1", self._hora(12, 20), 202)

        resultado = passagens._resultado_com_historico("ponto_externo_2")

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["ponto_anterior"], "Ponto Externo I / Alex")
        self.assertEqual(resultado["ponto_atual"], "Ponto Externo II / Canãa")
        self.assertFalse(resultado["ignorou_registro_incompativel"])

    def test_historico_tem_limite(self):
        """O histórico deve descartar os registros mais antigos ao passar do limite."""
        for indice in range(passagens.MAX_HISTORICO_REGISTROS + 5):
            passagens._registrar_no_historico(
                "fitotecnia",
                self._hora(12, indice % 60),
                indice,
            )

        historico = passagens.obter_historico()

        self.assertEqual(len(historico), passagens.MAX_HISTORICO_REGISTROS)

    def test_limpar_estado_tambem_limpa_historico(self):
        """Novo contexto operacional não pode herdar evidências do bloco anterior."""
        passagens._registrar_no_historico("ru", self._hora(12, 12), 301)

        passagens.limpar_estado()

        self.assertEqual(passagens.obter_historico(), [])


if __name__ == "__main__":
    unittest.main()
