import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from regras import (
    estimar_chegada_portao_1,
    listar_horarios_periodo,
    montar_resumo_horarios,
    montar_rota_atual,
    estado_vazio,
    registrar_passagem,
)

FUSO = timezone(timedelta(hours=-3))


class TestRegrasCloudflare(unittest.TestCase):
    def test_estimativa_1300_nao_e_pico(self):
        previsao = estimar_chegada_portao_1("13:00")
        self.assertFalse(previsao["pico"])
        self.assertEqual(previsao["inicio"], "13:15")
        self.assertEqual(previsao["fim"], "13:20")

    def test_estimativa_1325_nao_e_pico(self):
        previsao = estimar_chegada_portao_1("13:25")
        self.assertFalse(previsao["pico"])
        self.assertEqual(previsao["inicio"], "13:40")
        self.assertEqual(previsao["fim"], "13:45")

    def test_listagem_tarde_contem_1300_e_1600(self):
        texto = listar_horarios_periodo("tarde")
        self.assertIn("13:00", texto)
        self.assertIn("16:00", texto)

    def test_resumo_noturno_aponta_2040(self):
        agora = datetime(2026, 8, 11, 19, 0, tzinfo=FUSO)
        self.assertIn("20:40", montar_resumo_horarios(agora))

    def test_rota_contem_biblioteca_duas_vezes(self):
        self.assertEqual(montar_rota_atual().count("Biblioteca"), 2)

    def test_primeiro_registro_e_duplicata(self):
        estado = estado_vazio()
        agora = datetime(2026, 8, 11, 13, 5, tzinfo=FUSO)
        estado, resultado = registrar_passagem(estado, "fitotecnia", 1, agora)
        self.assertTrue(resultado["aceito"])
        estado, resultado = registrar_passagem(estado, "fitotecnia", 2, agora)
        self.assertFalse(resultado["aceito"])
        self.assertEqual(resultado["motivo"], "duplicado")


if __name__ == "__main__":
    unittest.main()
