import entry_core as _core
from entry_core import *


def teclado_localizacao():
    return {
        "inline_keyboard": [
            [{"text": "🔄 Onde está o ônibus?", "callback_data": "onde"}],
            [{"text": "📍 Marcar ponto", "callback_data": "local"}],
            [{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}],
        ]
    }


class Default(_core.Default):
    async def _onde(self, chat_id):
        principal = await self._estado().localizacao()
        texto = "🚌 <b>CIRCULAR PRINCIPAL</b>\n\n" + principal["texto"]
        avisos = await self._avisos_ativos()
        impacto = _core.impacto_localizacao(avisos)
        if impacto:
            texto += "\n\n" + impacto
        status = await self._status_micro()
        if status.get("ativo"):
            micro = await self._estado().localizacao_micro()
            estado_micro = micro.get("estado") or {}
            texto_micro = (
                micro.get("texto")
                if estado_micro.get("horario") and estado_micro.get("ponto_atual")
                else _core.referencia_micro_sem_ponto()
            )
            tempo = _core.tempo_micro(status)
            texto += (
                "\n\n────────────\n\n🚐 <b>MICRO — REFORÇO</b>"
                + ("\n" + tempo if tempo else "")
                + "\n\n"
                + texto_micro
            )
        return await _core.enviar_mensagem(
            self.env.TELEGRAM_BOT_TOKEN,
            chat_id,
            texto,
            parse_mode="HTML",
            reply_markup=teclado_localizacao(),
        )
