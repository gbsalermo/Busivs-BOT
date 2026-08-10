import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import passagens


class TestBlocosOperacionais(unittest.TestCase):

    def setUp(self):
        passagens.limpar_estado()

    def _definir_estado(self, horario: datetime):
        passagens._estado.update(
            {
                "ponto_anterior": "fitotecnia",
                "ponto_atual": "pavilhao_1",
                "horario": horario,
                "telegram_id": 123,
                "resultado_rota": None,
            }
        )

    # ---------------------------------------------------------
    # 1. Viagens próximas devem continuar no mesmo bloco
    # ---------------------------------------------------------

    def test_0650_continua_no_mesmo_bloco_de_0625(self):
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

    # ---------------------------------------------------------
    # 2. Lacuna grande deve encerrar o bloco
    # 07:55 -> 09:35 = 100 minutos
    # ---------------------------------------------------------

    def test_inicio_0935_expira_estado_do_bloco_anterior(self):
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

    # ---------------------------------------------------------
    # 3. Viagens do novo bloco podem compartilhar contexto
    # 09:35 -> 10:00 = 25 minutos
    # ---------------------------------------------------------

    def test_1000_mantem_confirmacao_do_bloco_iniciado_0935(self):
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

    # ---------------------------------------------------------
    # 4. Limite exato de 60 minutos ainda é mesmo bloco
    # ---------------------------------------------------------

    def test_intervalo_de_exatos_60_minutos_nao_quebra_bloco(self):
        horarios = [
            {"hora": "10:00", "origem": "Garagem"},
            {"hora": "11:00", "origem": "Garagem"},
        ]

        agora = datetime(
            2026, 8, 10, 11, 0,
            tzinfo=passagens.FUSO_LOCAL
        )

        with patch.object(
            passagens,
            "_carregar_horarios_principal",
            return_value=horarios
        ):
            quebra = passagens._quebra_de_bloco_mais_recente(agora)

        self.assertIsNone(quebra)

    # ---------------------------------------------------------
    # 5. Acima de 60 minutos deve quebrar
    # ---------------------------------------------------------

    def test_intervalo_de_61_minutos_quebra_bloco(self):
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

    # ---------------------------------------------------------
    # 6. Mudança de dia sempre expira
    # ---------------------------------------------------------

    def test_estado_do_dia_anterior_expira(self):
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

    # ---------------------------------------------------------
    # 7. Estado vazio nunca precisa expirar
    # ---------------------------------------------------------

    def test_estado_vazio_nao_expira(self):
        agora = datetime(
            2026, 8, 10, 10, 0,
            tzinfo=passagens.FUSO_LOCAL
        )

        passagens.limpar_estado()

        self.assertFalse(passagens._estado_expirou(agora))

    # ---------------------------------------------------------
    # 8. Detectar quebra real existente nos horários atuais
    # ---------------------------------------------------------

    def test_horarios_reais_detectam_quebra_entre_0755_e_0935(self):
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