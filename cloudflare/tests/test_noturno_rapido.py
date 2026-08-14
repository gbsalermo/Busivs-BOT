import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from blocos_operacionais import blocos_no_dia
from regras import estimar_chegada_portao_1, viagem_em_retorno

FUSO = timezone(timedelta(hours=-3))


class TestNoturnoRapido(unittest.TestCase):
    def test_previsoes_noturnas_rapidas(self):
        esperadas = {
            "20:40": ("20:50", "20:55"),
            "21:40": ("21:50", "21:55"),
            "22:30": ("22:40", "22:45"),
        }
        for hora, (inicio, fim) in esperadas.items():
            with self.subTest(hora=hora):
                previsao = estimar_chegada_portao_1(hora)
                self.assertEqual(previsao["inicio"], inicio)
                self.assertEqual(previsao["fim"], fim)

    def test_retorno_comeca_sem_margem_extra_no_noturno_rapido(self):
        agora = datetime(2026, 8, 11, 20, 55, tzinfo=FUSO)
        retorno = viagem_em_retorno(agora=agora)
        self.assertIsNotNone(retorno)
        self.assertEqual(retorno["viagem"]["hora"], "20:40")
        self.assertEqual(retorno["inicio_retorno"], "20:55")

    def test_bloco_2040_fecha_cinco_minutos_depois_do_fim_p1(self):
        referencia = datetime(2026, 8, 11, 20, 40, tzinfo=FUSO)
        bloco = next(b for b in blocos_no_dia(referencia) if b["id"] == "noite_2040")
        self.assertEqual(bloco["fim_p1"].strftime("%H:%M"), "20:55")
        self.assertEqual(bloco["fim_base"].strftime("%H:%M"), "21:00")


if __name__ == "__main__":
    unittest.main()
