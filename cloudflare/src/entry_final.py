import entry_core as _core
from entry_core import *


def teclado_localizacao(admin=False):
    linhas = [
        [{"text": "🔄 Onde está o ônibus?", "callback_data": "onde"}],
        [{"text": "📍 Marcar ponto", "callback_data": "local"}],
    ]
    if admin:
        linhas.append([{"text": "↩️ Retornar à volta anterior", "callback_data": "admin_volta_anterior"}])
    linhas.append([{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}])
    return {"inline_keyboard": linhas}


def teclado_menu_com_controle(micro_ativo=False, admin=False, principal_ativo=True):
    teclado = _core.teclado_menu(micro_ativo, admin, principal_ativo)
    if not admin:
        return teclado
    linhas = list(teclado.get("inline_keyboard", []))
    botao = [{"text": "↩️ Retornar à volta anterior", "callback_data": "admin_volta_anterior"}]
    indice_ajuda = next((i for i, linha in enumerate(linhas) if any(b.get("callback_data") == "ajuda" for b in linha)), len(linhas))
    linhas.insert(indice_ajuda, botao)
    return {"inline_keyboard": linhas}


class Default(_core.Default):
    async def _menu(self, chat_id, telegram_id=None, boas_vindas=False):
        status_micro = await self._status_micro()
        status_principal = await self._status_principal()
        admin = self._telegram_admin(telegram_id)
        if boas_vindas:
            await _core.enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "👋 Bem-vindo ao BUSIVS!\n\nEm caso de dúvidas, clique em ❓ Ajuda ou fale com o administrador.")
        envio = await _core.enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "🚌 BUSIVS BOT\n\nEscolha uma opção:", reply_markup=teclado_menu_com_controle(status_micro.get("ativo"), admin, status_principal.get("ativo")))
        avisos = await self._avisos_ativos()
        if avisos:
            return await _core.enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, _core.texto_avisos(avisos))
        return envio

    async def _onde(self, chat_id, telegram_id=None):
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
            texto_micro = micro.get("texto") if estado_micro.get("horario") and estado_micro.get("ponto_atual") else _core.referencia_micro_sem_ponto()
            tempo = _core.tempo_micro(status)
            texto += "\n\n────────────\n\n🚐 <b>MICRO — REFORÇO</b>" + ("\n" + tempo if tempo else "") + "\n\n" + texto_micro
        return await _core.enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, texto, parse_mode="HTML", reply_markup=teclado_localizacao(self._telegram_admin(telegram_id)))

    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao == "onde":
            return await self._onde(chat_id, telegram_id)
        if acao == "admin_volta_anterior":
            if not self._telegram_admin(telegram_id):
                return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            resultado = await self._estado().retornar_volta_anterior()
            if not resultado.get("ok"):
                texto = "⚠️ Não há uma volta anterior disponível para selecionar."
            else:
                texto = "↩️ Referência ajustada manualmente.\n\n" + f"🕐 Volta atual: {resultado['hora']} — {resultado.get('origem', '')}\n" + "📌 As confirmações já registradas foram mantidas."
            return await _core.enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, texto, reply_markup=teclado_localizacao(True))
        return await super()._acao(acao, chat_id, telegram_id)
