import unittest
from datetime import datetime, timedelta

from seguranca_local import SegurancaColaborativa


class SegurancaColaborativaTest(unittest.TestCase):
    def setUp(self):
        self.seg = SegurancaColaborativa()
        self.agora = datetime(2026, 8, 12, 20, 0, 0)

    def test_primeira_confirmacao_e_permitida(self):
        r = self.seg.verificar(1, "principal", "biblioteca", self.agora)
        self.assertTrue(r["permitido"])

    def test_mesmo_ponto_recente_nao_reescreve_estado(self):
        self.seg.registrar_confirmacao("principal", "biblioteca", self.agora)
        r = self.seg.verificar(2, "principal", "biblioteca", self.agora + timedelta(seconds=5))
        self.assertFalse(r["permitido"])
        self.assertEqual(r["motivo"], "ponto_ja_confirmado")

    def test_cliques_rapidos_do_mesmo_usuario_sao_limitados(self):
        self.assertTrue(self.seg.verificar(1, "principal", "ru", self.agora)["permitido"])
        r = self.seg.verificar(1, "principal", "fitotecnia", self.agora + timedelta(seconds=1))
        self.assertFalse(r["permitido"])
        self.assertEqual(r["motivo"], "rapido_demais")

    def test_tres_pontos_distintos_em_rajada_geram_cooldown(self):
        self.assertTrue(self.seg.verificar(1, "principal", "ru", self.agora)["permitido"])
        self.assertTrue(self.seg.verificar(1, "principal", "fitotecnia", self.agora + timedelta(seconds=3))["permitido"])
        r = self.seg.verificar(1, "principal", "biblioteca", self.agora + timedelta(seconds=6))
        self.assertFalse(r["permitido"])
        self.assertEqual(r["motivo"], "conflito_usuario")

    def test_cooldown_bloqueia_novas_confirmacoes(self):
        self.seg.verificar(1, "principal", "ru", self.agora)
        self.seg.verificar(1, "principal", "fitotecnia", self.agora + timedelta(seconds=3))
        self.seg.verificar(1, "principal", "biblioteca", self.agora + timedelta(seconds=6))
        r = self.seg.verificar(1, "principal", "pavilhao_1", self.agora + timedelta(seconds=10))
        self.assertFalse(r["permitido"])
        self.assertEqual(r["motivo"], "cooldown")


if __name__ == "__main__":
    unittest.main()
