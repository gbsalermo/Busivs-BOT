import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from blocos_operacionais import blocos_no_dia, fim_efetivo_bloco
from regras import MARCADOR_FIM_BLOCO, estado_vazio, registrar_passagem
from validacao_rota import validar_deslocamento

FUSO = timezone(timedelta(hours=-3))


def estado_no_portao_1(horario):
    return {
        "ponto_anterior": "ponto_externo_2",
        "ponto_atual": "portao_1",
        "horario": horario.isoformat(),
        "telegram_id": 1,
        "resultado_rota": {
            "ponto_atual_id": "portao_1",
            "indice_atual": 10,
            "sentido": "RU",
            "proximo": {"id": "biblioteca", "nome": "Biblioteca", "opcional": False},
        },
        "historico": [{"ponto_id": "portao_1", "horario": horario.isoformat(), "telegram_id": 1}],
    }


class TestRetornoGaragem(unittest.TestCase):
    def test_fitotecnia_liberada_depois_portao1_na_ultima_volta(self):
        agora = datetime(2026, 8, 11, 10, 25, tzinfo=FUSO)
        estado = estado_no_portao_1(datetime(2026, 8, 11, 10, 20, tzinfo=FUSO))
        bloqueio = validar_deslocamento(
            estado, "fitotecnia", agora,
            exigir_nova_saida_para_ciclo=True,
        )
        self.assertIsNone(bloqueio)
        estado, resultado = registrar_passagem(estado, "fitotecnia", 2, agora)
        self.assertTrue(resultado["aceito"])
        self.assertTrue(resultado["retorno_garagem"])
        self.assertEqual(resultado["resultado_rota"]["sentido"], "GARAGEM")

    def test_garagem_rejeitada_sem_evidencia_de_retorno(self):
        agora = datetime(2026, 8, 11, 10, 10, tzinfo=FUSO)
        estado = estado_vazio()
        bloqueio = validar_deslocamento(
            estado, "garagem", agora,
            exigir_nova_saida_para_ciclo=True,
        )
        self.assertIsNotNone(bloqueio)
        self.assertEqual(bloqueio["motivo"], "ordem_rota_invalida")

    def test_garagem_encerra_bloco_imediatamente(self):
        agora = datetime(2026, 8, 11, 10, 30, tzinfo=FUSO)
        estado = estado_no_portao_1(datetime(2026, 8, 11, 10, 20, tzinfo=FUSO))
        self.assertIsNone(validar_deslocamento(
            estado, "garagem", agora,
            exigir_nova_saida_para_ciclo=True,
        ))
        estado, resultado = registrar_passagem(estado, "garagem", 3, agora)
        self.assertTrue(resultado["bloco_encerrado"])
        self.assertTrue(estado["resultado_rota"][MARCADOR_FIM_BLOCO])
        self.assertTrue(estado["resultado_rota"]["garagem_confirmada"])

        bloco = next(b for b in blocos_no_dia(agora) if b["id"] == "manha_intermediario")
        self.assertEqual(fim_efetivo_bloco(bloco, estado), bloco["inicio_dt"])

    def test_micro_nao_recebe_excecao_de_retorno_garagem(self):
        agora = datetime(2026, 8, 11, 12, 40, tzinfo=FUSO)
        estado = estado_no_portao_1(datetime(2026, 8, 11, 12, 35, tzinfo=FUSO))
        bloqueio = validar_deslocamento(
            estado, "garagem", agora,
            permitir_ciclo=False,
            exigir_nova_saida_para_ciclo=False,
        )
        self.assertIsNotNone(bloqueio)


if __name__ == "__main__":
    unittest.main()
