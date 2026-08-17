import entry_core as _core
from entry_core import *

from dados import BLOCOS_PRINCIPAL, HORARIOS

FEEDBACK_PROMPT = "💬 Envie seu feedback sobre o BUSIVS respondendo a esta mensagem."
MAX_FEEDBACK = 2000


def teclado_localizacao(admin=False):
    linhas = [
        [{"text": "🔄 Onde está o ônibus?", "callback_data": "onde"}],
        [{"text": "📍 Marcar ponto", "callback_data": "local"}],
    ]
    if admin:
        linhas.append([{"text": "🧭 Escolher volta de referência", "callback_data": "admin_ref_menu"}])
        linhas.append([{"text": "🅿️ Garagem / Encerrar bloco", "callback_data": "admin_ref_garagem"}])
    linhas.append([{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}])
    return {"inline_keyboard": linhas}


def teclado_ajuda_com_feedback():
    return {"inline_keyboard": [
        [{"text": "🗺️ Rota atual", "callback_data": "rota"}],
        [{"text": "📖 Dicas para uso do BOT", "callback_data": "manual"}],
        [{"text": "💬 Enviar feedback", "callback_data": "feedback"}],
        [{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}],
    ]}


# entry_core usa a função global teclado_ajuda dentro dos handlers herdados.
# Substituí-la aqui mantém rota/manual/ajuda consistentes sem duplicar handlers.
_core.teclado_ajuda = teclado_ajuda_com_feedback


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

        if acao == "feedback":
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                FEEDBACK_PROMPT + "\n\nPode enviar sugestão, problema encontrado ou algo que tenha ficado confuso.",
                reply_markup={
                    "force_reply": True,
                    "selective": True,
                    "input_field_placeholder": "Escreva seu feedback...",
                },
            )

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

    @staticmethod
    def _eh_resposta_feedback(mensagem):
        resposta = mensagem.get("reply_to_message") or {}
        texto_prompt = (resposta.get("text") or "").strip()
        return texto_prompt.startswith(FEEDBACK_PROMPT)

    async def _receber_feedback(self, mensagem, chat_id, usuario):
        texto = (mensagem.get("text") or "").strip()
        if not texto:
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "⚠️ O feedback precisa ser enviado como texto.",
                reply_markup=teclado_ajuda_com_feedback(),
            )
        if len(texto) > MAX_FEEDBACK:
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                f"⚠️ Seu feedback ficou muito grande. Envie até {MAX_FEEDBACK} caracteres.",
                reply_markup=teclado_ajuda_com_feedback(),
            )

        remetente = mensagem.get("from") or {}
        nome = " ".join(filter(None, [remetente.get("first_name"), remetente.get("last_name")])).strip() or "Usuário"
        username = remetente.get("username")
        identificacao = f"@{username}" if username else "sem @username"
        texto_admin = (
            "💬 NOVO FEEDBACK — BUSIVS\n\n"
            f"👤 {nome}\n"
            f"🔗 {identificacao}\n"
            f"🆔 Telegram ID: {usuario}\n\n"
            "📝 Feedback:\n"
            f"{texto}"
        )

        admin_chat_id = str(self.env.ADMIN_TELEGRAM_ID).strip()
        envio_admin = await _core.enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, admin_chat_id, texto_admin)
        if not envio_admin.get("ok_http"):
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "⚠️ Não consegui enviar seu feedback agora. Tente novamente mais tarde.",
                reply_markup=teclado_ajuda_com_feedback(),
            )

        return await _core.enviar_mensagem(
            self.env.TELEGRAM_BOT_TOKEN,
            chat_id,
            "✅ Feedback enviado. Obrigado por ajudar a melhorar o BUSIVS!",
            reply_markup=teclado_ajuda_com_feedback(),
        )

    async def fetch(self, request):
        parsed = _core.urlparse(request.url)
        caminho = parsed.path
        method = request.method

        if method == "GET" and caminho == "/health":
            return _core.Response.json({"status": "ok", "service": "busivs-bot", "runtime": "cloudflare-worker", "stage": "production-micro"})
        if method == "POST" and caminho == "/admin/telegram/set-webhook":
            if not self._admin_ok(request):
                return _core.Response.json({"ok": False, "error": "admin_secret_invalid"}, status=403)
            url = f"{parsed.scheme}://{parsed.netloc}/telegram/webhook"
            r = await _core.configurar_webhook(self.env.TELEGRAM_BOT_TOKEN, url, self.env.TELEGRAM_WEBHOOK_SECRET)
            return _core.Response.json({"ok": r["ok_http"], "webhook_url": url}, status=200 if r["ok_http"] else 502)
        if method == "POST" and caminho == "/admin/telegram/delete-webhook":
            if not self._admin_ok(request):
                return _core.Response.json({"ok": False, "error": "admin_secret_invalid"}, status=403)
            r = await _core.remover_webhook(self.env.TELEGRAM_BOT_TOKEN)
            return _core.Response.json({"ok": r["ok_http"]}, status=200 if r["ok_http"] else 502)
        if method == "POST" and caminho == "/telegram/webhook":
            segredo = request.headers.get(_core.HEADER_SEGREDO_TELEGRAM)
            if not segredo or segredo != self.env.TELEGRAM_WEBHOOK_SECRET:
                return _core.Response.json({"ok": False, "error": "webhook_secret_invalid"}, status=403)
            try:
                update = await request.json()
            except Exception:
                return _core.Response.json({"ok": False, "error": "invalid_json"}, status=400)

            mensagem = update.get("message") or update.get("edited_message")
            if mensagem:
                chat_id = (mensagem.get("chat") or {}).get("id")
                usuario = (mensagem.get("from") or {}).get("id")
                if chat_id is None:
                    return _core.Response.json({"ok": True, "handled": False})
                texto = (mensagem.get("text") or "").strip()

                if self._eh_resposta_feedback(mensagem) and not texto.startswith("/"):
                    envio = await self._receber_feedback(mensagem, chat_id, usuario)
                else:
                    aguardando = await self._estado().aguardando_aviso_personalizado()
                    if aguardando.get("ativo") and self._telegram_admin(usuario) and not texto.startswith("/"):
                        resultado = await self._estado().salvar_aviso_personalizado(texto)
                        envio = await _core.enviar_mensagem(
                            self.env.TELEGRAM_BOT_TOKEN,
                            chat_id,
                            ("✅ Aviso personalizado publicado." if resultado.get("ok") else "⚠️ Não consegui publicar esse aviso.") + "\n\n" + _core.texto_avisos(resultado.get("avisos", []), True),
                            reply_markup=_core.teclado_admin_avisos((await self._status_micro()).get("ativo")),
                        )
                    elif texto == "/start":
                        envio = await self._menu(chat_id, usuario, boas_vindas=True)
                    else:
                        comandos = {"/onde": "onde", "/local": "local", "/rota": "rota", "/horarios": "horarios", "/listar_horarios": "listar_horarios"}
                        envio = await self._acao(comandos.get(texto, "desconhecido"), chat_id, usuario)
                return _core.Response.json({"ok": envio["ok_http"], "handled": True}, status=200 if envio["ok_http"] else 502)

            callback = update.get("callback_query")
            if callback:
                cid = callback.get("id")
                if cid:
                    await _core.responder_callback(self.env.TELEGRAM_BOT_TOKEN, cid)
                chat_id = ((callback.get("message") or {}).get("chat") or {}).get("id")
                if chat_id is None:
                    return _core.Response.json({"ok": True, "handled": False})
                usuario = (callback.get("from") or {}).get("id")
                acao = callback.get("data") or ""
                envio = await self._acao(acao, chat_id, usuario)
                return _core.Response.json({"ok": envio["ok_http"], "handled": True, "callback": acao}, status=200 if envio["ok_http"] else 502)
            return _core.Response.json({"ok": True, "handled": False})

        return _core.Response.json({"service": "BUSIVS BOT", "status": "cloudflare-running", "health": "/health", "webhook": "/telegram/webhook"})
