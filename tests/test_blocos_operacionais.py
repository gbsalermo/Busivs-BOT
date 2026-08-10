"""Testes do ciclo de vida do estado por blocos operacionais.

O objetivo aqui é garantir que o BUSIVS não apague a localização a cada nova
saída, mas também não carregue uma confirmação antiga para um bloco muito
depois. A fronteira atual é um intervalo maior que 60 minutos entre saídas.
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

# Permite importar diretamente os módulos de ``src`` durante os testes.
RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import passagens


class TestBlocosOperacionais(unittest.TestCase):
    """Valida quando o estado colaborativo deve ser mantido ou descartado."""

    def setUp(self):
        """Começa cada teste sem estado/histórico deixado pelo teste anterior."""
        passagens.limpar_estado()

    def _definir_estado(self, horario: datetime):
        """Cria um estado mínimo conhecido para testar apenas a expiração."""
        passagens._estado.update(
            {
                "ponto_anterior": "fitotecnia",
                "ponto_atual": "pavilhao_1",
                "horario": horario,
                "telegram_id": 123,
                "resultado_rota": None,
            }
        )

    # Viagens próximas devem continuar no mesmo bloco.
    def test_0650_continua_no_mesmo_bloco_de_0625(self):
        """06:25 -> 06:50 não deve apagar uma confirmação ainda útil."""
        horario_confirmacao = datetime(
            2026, 8, 10, 6, 40,
            tzinfo=passagens.FUSO_LOCAL
        )

        agora = datetime(
            2026, 8, 10, 6, 50,
            tzinfo=passagens.FUSO_LOCAL
        )

        self._definir_estado(horario_confirmacao)

        self.assertFalse(passagens._estado_expirou(agora))

    def test_0755_continua_no_bloco_da_manha(self):
        """Uma confirmação do bloco da manhã ainda vale na saída das 07:55."""
        horario_confirmacao = datetime(
            2026, 8, 10, 7, 30,
            tzinfo=passagens.FUSO_LOCAL
        )

        agora = datetime(
            2026, 8, 10, 7, 55,
            tzinfo=passagens.FUSO_LOCAL
        )

        self._definir_estado(horario_confirmacao)

        self.assertFalse(passagens._estado_expirou(agora))

    # 07:55 -> 09:35 = 100 minutos: lacuna grande encerra o bloco.
    def test_inicio_0935_expira_estado_do_bloco_anterior(self):
        """Ao iniciar 09:35, estado anterior à quebra deve estar expirado."""
        horario_confirmacao = datetime(
            2026, 8, 10, 7, 50,
            tzinfo=passagens.FUSO_LOCAL
        )

        agora = datetime(
            2026, 8, 10, 9, 35,
            tzinfo=passagens.FUSO_LOCAL
        )

        self._definir_estado(horario_confirmacao)

        self.assertTrue(passagens._estado_expirou(agora))

    def test_estado_antigo_de_0755_nao_sobrevive_ao_bloco_0935(self):
        """A rotina de limpeza deve efetivamente zerar estado antigo."""
        horario_confirmacao = datetime(
            2026, 8, 10, 7, 55,
            tzinfo=passagens.FUSO_LOCAL
        )

        agora = datetime(
            2026, 8, 10, 10, 0,
            tzinfo=passagens.FUSO_LOCAL
        )

        self._definir_estado(horario_confirmacao)

        passagens._limpar_estado_se_expirado(agora)

        estado = passagens.obter_estado()

        self.assertIsNone(estado["ponto_atual"])
        self.assertIsNone(estado["horario"])

    # 09:35 -> 10:00 = 25 minutos: o novo bloco compartilha contexto.
    def test_1000_mantem_confirmacao_do_bloco_iniciado_0935(self):
        """09:35 e 10:00 pertencem ao mesmo bloco operacional."""
        horario_confirmacao = datetime(
            2026, 8, 10, 9, 45,
            tzinfo=passagens.FUSO_LOCAL
        )

        agora = datetime(
            2026, 8, 10, 10, 0,
            tzinfo=passagens.FUSO_LOCAL
        )

        self._definir_estado(horario_confirmacao)

        self.assertFalse(passagens._estado_expirou(agora))

    def test_intervalo_de_exatos_60_minutos_nao_quebra_bloco(self):
        """O limite é inclusivo: exatamente 60 minutos ainda é o mesmo bloco."""
        horarios = [
            {"hora": "10:00", "origem": "Garagem"},
            {"hora": "11:00", "origem": "Garagem"},
        ]

        agora = datetime(
            2026, 8, 10, 11, 0,
            tzinfo=passagens.FUSO_LOCAL
        )

        # Substitui temporariamente o JSON real por uma lista controlada para
        # testar exatamente a fronteira de 60 minutos.
        with patch.object(
            passagens,
            "_carregar_horarios_principal",
            return_value=horarios
        ):
            quebra = passagens._quebra_de_bloco_mais_recente(agora)

        self.assertIsNone(quebra)

    def test_intervalo_de_61_minutos_quebra_bloco(self):
        """Um minuto acima do limite já deve iniciar um novo bloco."""
        horarios = [
            {"hora": "10:00", "origem": "Garagem"},
            {"hora": "11:01", "origem": "Garagem"},
        ]

        agora = datetime(
            2026, 8, 10, 11, 1,
            tzinfo=passagens.FUSO_LOCAL
        )

        with patch.object(
            passagens,
            "_carregar_horarios_principal",
            return_value=horarios
        ):
            quebra = passagens._quebra_de_bloco_mais_recente(agora)

        self.assertIsNotNone(quebra)
        self.assertEqual(quebra.hour, 11)
        self.assertEqual(quebra.minute, 1)

    def test_estado_do_dia_anterior_expira(self):
        """Nenhuma confirmação deve atravessar a mudança de dia."""
        horario_confirmacao = datetime(
            2026, 8, 9, 22, 30,
            tzinfo=passagens.FUSO_LOCAL
        )

        agora = datetime(
            2026, 8, 10, 6, 0,
            tzinfo=passagens.FUSO_LOCAL
        )

        self._definir_estado(horario_confirmacao)

        self.assertTrue(passagens._estado_expirou(agora))

    def test_estado_vazio_nao_expira(self):
        """Sem confirmação não existe estado para invalidar."""
        agora = datetime(
            2026, 8, 10, 10, 0,
            tzinfo=passagens.FUSO_LOCAL
        )

        passagens.limpar_estado()

        self.assertFalse(passagens._estado_expirou(agora))

    def test_horarios_reais_detectam_quebra_entre_0755_e_0935(self):
        """O cadastro oficial atual deve conter a quebra real 07:55 -> 09:35."""
        agora = datetime(
            2026, 8, 10, 9, 35,
            tzinfo=passagens.FUSO_LOCAL
        )

        quebra = passagens._quebra_de_bloco_mais_recente(agora)

        self.assertIsNotNone(quebra)
        self.assertEqual(quebra.hour, 9)
        self.assertEqual(quebra.minute, 35)


if __name__ == "__main__":
    unittest.main()
