import entry_core as _core
from entry_core import *

from dados import BLOCOS_PRINCIPAL, HORARIOS


def teclado_localizacao(admin=False):
    linhas = [
        [{"text": "🔄 Onde está o ônibus?", "callback_data": "onde"}],
        [{"text": "📍 Marcar ponto", "callback_data": "local"}],
    ]
    if admin:
        linhas.append([{"text": "🧭 Escolher volta de referência", "callback_data": "admin_ref_menu"}])
    linhas.append([{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}])
    return {"inline_keyboard": linhas}


def teclado_menu_com_controle(micro_ativo=False, admin=False, principal_ativo=True):
    teclado = _core.teclado_menu(micro_ativo, admin, principal_ativo)
    if not admin:
        return teclado
    linhas = list(teclado.get("inline_keyboard", []))
    botao = [{"text": "🧭 Escolher volta de referência", "callback_data": "admin_ref_menu"}]
    indice_ajuda = next((i for i, linha in enumerate(linhas) if any(b.get("callback_data") == "ajuda" for b in linha)), len(linhas))
    linhas.insert(indice_ajuda, botao)
    return {"inline_keyboard": linhas}


def _minutos(hora):
    h, m = map(int, hora.split(":"))
    return h * 60 + m


def _bloco_referencia_atual():
    agora = _core.agora_local()
    minuto = agora.hour * 60 + agora.minute
    blocos = BLOCOS_PRINCIPAL

    for i, bloco in enumerate(blocos):
        inicio = _minutos(bloco["inicio"])
        proximo_inicio = _minutos(blocos[i + 1]["inicio"]) if i + 1 < len(blocos) else 24 * 60
        if inicio <= minuto < proximo_inicio:
            return bloco

    futuros = [b for b in blocos if _minutos(b["inicio"]) > minuto]
    return min(futuros, key=lambda b: _minutos(b["inicio"])) if futuros else blocos[-1]


def _horarios_do_bloco(bloco):
    horarios = HORARIOS.get("principal", [])
    inicio = next((i for i, h in enumerate(horarios) if h["hora"] == bloco["inicio"]), None)
    fim = next((i for i, h in enumerate(horarios) if h["hora"] == bloco["ultima"]), None)
    if inicio is None or fim is None or fim < inicio:
        return []
    return horarios[inicio:fim + 1]


def teclado_referencias():
    bloco = _bloco_referencia_atual()
    horarios = _horarios_do_bloco(bloco)
    botoes = [
        {"text": h["hora"], "callback_data": f"admin_ref_{h['hora'].replace(':', '')}"}
        for h in horarios
    ]
    linhas = [botoes[i:i + 3] for i in range(0, len(botoes), 3)]
    linhas.append([{"text": "🅿️ Garagem / Encerrar bloco", "callback_data": "admin_ref_garagem"}])
    linhas.append([{"text": "⬅️ Voltar", "callback_data": "onde"}])
    return {"inline_keyboard": linhas}, bloco


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

        if acao == "admin_ref_menu":
            if not self._telegram_admin(telegram_id):
                return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            teclado, bloco = teclado_referencias()
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                f"🧭 Escolha a volta de referência do bloco {bloco['inicio']}–{bloco['ultima']}:",
                reply_markup=teclado,
            )

        if acao == "admin_ref_garagem":
            if not self._telegram_admin(telegram_id):
                return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            resultado = await self._estado().encerrar_bloco_admin()
            if not resultado.get("ok"):
                texto = "⚠️ Não consegui identificar um bloco para encerrar."
            else:
                texto = (
                    "🅿️ Ônibus marcado na Garagem.\n\n"
                    f"✅ Bloco {resultado['inicio']}–{resultado['ultima']} encerrado manualmente."
                )
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                texto,
                reply_markup=teclado_localizacao(True),
            )

        if acao.startswith("admin_ref_"):
            if not self._telegram_admin(telegram_id):
                return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            bruto = acao.replace("admin_ref_", "", 1)
            if len(bruto) != 4 or not bruto.isdigit():
                return await _core.enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "⚠️ Referência inválida.", reply_markup=teclado_localizacao(True))
            hora = f"{bruto[:2]}:{bruto[2:]}"
            resultado = await self._estado().definir_volta_referencia(hora)
            if not resultado.get("ok"):
                texto = "⚠️ Não consegui selecionar essa volta."
            else:
                texto = (
                    "🧭 Referência ajustada manualmente.\n\n"
                    f"🕐 Volta atual: {resultado['hora']} — {resultado.get('origem', '')}\n"
                    "📌 As confirmações já registradas foram mantidas."
                )
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                texto,
                reply_markup=teclado_localizacao(True),
            )

        return await super()._acao(acao, chat_id, telegram_id)
