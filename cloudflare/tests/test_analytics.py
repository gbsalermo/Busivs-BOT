import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import analytics

FUSO = timezone(timedelta(hours=-3))


class StorageMemoria:
    def __init__(self):
        self.dados = {}

    async def get(self, chave):
        return self.dados.get(chave)

    async def put(self, chave, valor):
        self.dados[chave] = valor


class TestAnalytics(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.storage = StorageMemoria()
        self.agora_original = analytics.agora_local
        analytics.agora_local = lambda: datetime(2026, 8, 28, 12, 0, tzinfo=FUSO)

    async def asyncTearDown(self):
        analytics.agora_local = self.agora_original

    async def test_mesmo_usuario_conta_uma_vez_no_dia(self):
        await analytics.registrar_evento(self.storage, 101, "consulta_localizacao")
        await analytics.registrar_evento(self.storage, 101, "proximos_horarios")

        resumo = await analytics.resumo(self.storage, 1)
        self.assertEqual(resumo["usuarios_unicos"], 1)
        self.assertEqual(resumo["interacoes"], 2)
        self.assertEqual(resumo["total_registrado"], 1)
        self.assertEqual(resumo["eventos"]["consulta_localizacao"], 1)
        self.assertEqual(resumo["eventos"]["proximos_horarios"], 1)

    async def test_usuarios_diferentes_incrementam_total(self):
        await analytics.registrar_evento(self.storage, 101, "consulta_localizacao")
        await analytics.registrar_evento(self.storage, 202, "consulta_localizacao")

        resumo = await analytics.resumo(self.storage, 1)
        self.assertEqual(resumo["usuarios_unicos"], 2)
        self.assertEqual(resumo["total_registrado"], 2)

    async def test_admin_nao_contamina_metricas_publicas(self):
        await analytics.registrar_evento(self.storage, 999, "admin", admin=True)
        await analytics.registrar_evento(self.storage, 101, "consulta_localizacao")

        resumo = await analytics.resumo(self.storage, 1)
        self.assertEqual(resumo["usuarios_unicos"], 1)
        self.assertEqual(resumo["interacoes"], 1)
        self.assertEqual(resumo["admin_interacoes"], 1)
        self.assertEqual(resumo["total_registrado"], 1)

    async def test_evento_auxiliar_nao_duplica_interacao(self):
        await analytics.registrar_evento(self.storage, 101, "marcacao_principal")
        await analytics.registrar_evento(
            self.storage,
            101,
            "confirmacao_principal",
            contar_interacao=False,
        )

        resumo = await analytics.resumo(self.storage, 1)
        self.assertEqual(resumo["interacoes"], 1)
        self.assertEqual(resumo["eventos"]["confirmacao_principal"], 1)

    async def test_id_telegram_nao_e_salvo_em_claro(self):
        telegram_id = 123456789
        await analytics.registrar_evento(self.storage, telegram_id, "consulta_localizacao")

        serializado = json.dumps(self.storage.dados, ensure_ascii=False)
        self.assertNotIn(str(telegram_id), serializado)


if __name__ == "__main__":
    unittest.main()
