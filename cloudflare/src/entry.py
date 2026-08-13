from datetime import datetime
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

from estado_bus import BusState
from dados import PONTOS, ROTULOS_PONTOS
from micro import proxima_volta_micro, resumo_micro, volta_micro_atual
from regras import agora_local, listar_horarios_periodo, montar_rota_atual
from telegram_api import configurar_webhook, enviar_mensagem, remover_webhook, responder_callback

HEADER_SEGREDO_TELEGRAM = "X-Telegram-Bot-Api-Secret-Token"
HEADER_ADMIN = "X-BUSIVS-Admin-Secret"

AVISOS_PREDEFINIDOS = [
    "🚪 Portão 1 fechado",
    "🚪 Portão 2 fechado",
    "⚠️ Circular operando com atraso",
    "🛠️ Circular temporariamente fora de operação",
    "🛠️ Circular quebrou em meio ao trajeto",
    "🌧️ Tempo chuvoso, circular pode demorar mais do que o esperado",
    "🧍‍♂️🧍‍♀️ Superlotação do circular",
    "🚐 Micro está rodando!",
    "🚌 Rota alterada temporariamente",
    "📅 Horários especiais hoje",
]

MANUAL = """📖 Dicas para uso do BUSIVS

🚌 Onde está o ônibus?
Mostra a última confirmação colaborativa e a estimativa do trajeto. Se o micro estiver ativo, os dois veículos aparecem separados.

📍 Informar ponto atual
Use somente quando você acabou de ver o veículo passar. Se o micro estiver ativo, escolha primeiro qual veículo você viu.

⏰ Próximos horários
Mostra as próximas referências do circular principal. Quando o micro estiver em operação, também exibe a referência do reforço.

📋 Listar horários
Consulta os horários oficiais do circular principal por período.

🚐 Confirmar que o micro está rodando
Use somente quando você realmente vir o micro-ônibus de reforço operando. Depois de confirmado, o botão ficará verde e não precisará ser confirmado novamente.

📢 Avisos operacionais
Quando houver alguma ocorrência importante, os avisos aparecem automaticamente no bot.

❗ As localizações são colaborativas e os horários são referências oficiais. Atrasos e alterações podem acontecer.
🤝 Informe pontos apenas quando realmente tiver visto o veículo.

👤 Administrador do BUSIVS
📱 75 99978-0174"""


def teclado_voltar():
    return {"inline_keyboard": [[{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}]]}


def teclado_menu(micro_ativo=False, admin=False):
    micro = {"text": "🚐 Micro em operação ✅", "callback_data": "micro_ativo"} if micro_ativo else {"text": "🚐 Confirmar que o micro está rodando", "callback_data": "micro_confirmar"}
    linhas = [
        [{"text": "🚌 Onde está o ônibus?", "callback_data": "onde"}],
        [{"text": "📍 Informar ponto atual", "callback_data": "local"}],
        [{"text": "⏰ Próximos horários", "callback_data": "horarios"}],
        [{"text": "📋 Listar horários", "callback_data": "listar_horarios"}],
        [micro],
    ]
    if admin:
        linhas.append([{"text": "📢 Avisos", "callback_data": "avisos"}])
    linhas.append([{"text": "❓ Ajuda", "callback_data": "ajuda"}])
    return {"inline_keyboard": linhas}


def teclado_confirmar_micro():
    return {"inline_keyboard": [
        [{"text": "✅ Sim, está rodando", "callback_data": "micro_confirmar_sim"}],
        [{"text": "❌ Voltar", "callback_data": "menu"}],
    ]}


def teclado_ajuda():
    return {"inline_keyboard": [
        [{"text": "🗺️ Rota atual", "callback_data": "rota"}],
        [{"text": "📖 Dicas para uso do BOT", "callback_data": "manual"}],
        [{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}],
    ]}


def teclado_periodos():
    return {"inline_keyboard": [
        [{"text": "🌅 Manhã", "callback_data": "periodo_manha"}, {"text": "🍽️ Almoço", "callback_data": "periodo_meio_dia"}],
        [{"text": "🌤️ Tarde", "callback_data": "periodo_tarde"), {"text": "🌙 Noite", "callback_data": "periodo_noite"}],
        [{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}],
    ]}


def teclado_pontos(prefixo):
    botoes = [{"text": ROTULOS_PONTOS.get(pid, p["nome"]), "callback_data": f"{prefixo}_{pid}"} for pid, p in PONTOS.items()]
    linhas = [botoes[i:i + 2] for i in range(0, len(botoes), 2)]
    linhas.append([{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}])
    return {"inline_keyboard": linhas}


def teclado_veiculo():
    return {"inline_keyboard": [
        [{"text": "🚌 Circular principal", "callback_data": "veiculo_principal"}],
        [{"text": "🚐 Micro — reforço", "callback_data": "veiculo_micro"}],
        [{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}],
    ]}


def teclado_admin_avisos(micro_ativo=False):
    linhas = [[{"text": texto, "callback_data": f"aviso_add_{i}"}] for i, texto in enumerate(AVISOS_PREDEFINIDOS)]
    linhas += [
        [{"text": "✏️ Aviso personalizado", "callback_data": "aviso_personalizado"}],
        [{"text": "🗑️ Remover aviso", "callback_data": "aviso_remover_menu"}],
        [{"text": "🧹 Limpar todos", "callback_data": "aviso_limpar"}],
    ]
    if micro_ativo:
        linhas.append([{"text": "🚐 Desativar micro", "callback_data": "micro_desativar"}])
    linhas.append([{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}])
    return {"inline_keyboard": linhas}


def teclado_remover_avisos(avisos):
    linhas = []
    for i, texto in enumerate(avisos):
        rotulo = texto if len(texto) <= 45 else texto[:42] + "..."
        linhas.append([{"text": f"❌ {rotulo}", "callback_data": f"aviso_rem_{i}"}])
    linhas.append([{"text": "⬅️ Voltar aos avisos", "callback_data": "avisos"}])
    return {"inline_keyboard": linhas}


def texto_avisos(avisos, contador=False):
    sufixo = f" ({len(avisos)}/3)" if contador else ""
    if not avisos:
        return f"📢 Avisos{sufixo}\n\nNenhum aviso operacional ativo no momento."
    return "\n".join([f"📢 Avisos ativos{sufixo}", ""] + [f"• {a}" for a in avisos])


def limitar_resumo_principal(texto, quantidade=2):
    linhas = texto.splitlines()
    marcador = f"<b>{quantidade + 1}ª volta</b>"
    inicio = next((i for i, linha in enumerate(linhas) if marcador in linha), None)
    if inicio is None:
        return texto
    rodape = next((i for i in range(inicio, len(linhas)) if linhas[i].startswith("⚠️ <b>Horários de pico</b>") or linhas[i].startswith("ℹ️ Horários do Portão 1")), None)
    if rodape is None:
        return "\n".join(linhas[:inicio]).rstrip()
    return "\n".join(linhas[:inicio] + linhas[rodape:]).strip()


def tempo_micro(status):
    valor = status.get("ativado_em")
    if not valor:
        return ""
    try:
        inicio = datetime.fromisoformat(str(valor))
        minutos = max(0, int((agora_local() - inicio).total_seconds() // 60))
    except Exception:
        return ""
    if minutos < 1:
        return "🕐 Operação confirmada agora."
    if minutos == 1:
        return "🕐 Operação confirmada há 1 min."
    return f"🕐 Operação confirmada há {minutos} min."


def referencia_micro_sem_ponto():
    atual = volta_micro_atual()
    proxima = proxima_volta_micro()
    linhas = ["⚪ Sem confirmação de ponto recente."]
    if atual:
        linhas += ["", "🔵 <b>Referência atual do micro</b>", f"🕐 <b>{atual['inicio'].strftime('%H:%M')}</b> — {atual['origem']}"]
    if proxima:
        linhas += ["", "🟢 <b>Próxima referência</b>", f"🕐 <b>{proxima['inicio'].strftime('%H:%M')}</b> — {proxima['origem']}"]
    if not atual and not proxima:
        linhas += ["", "ℹ️ Não há referência oficial do micro neste momento."]
    return "\n".join(linhas)


def impacto_localizacao(avisos):
    mensagens = []
    if "🛠️ Circular temporariamente fora de operação" in avisos:
        return "🚨 O circular foi informado como temporariamente fora de operação. A última localização não garante que o veículo continue em movimento."
    if "🛠️ Circular quebrou em meio ao trajeto" in avisos:
        return "🚨 Há aviso de quebra durante o trajeto. A volta atual pode não ser concluída."
    if "⚠️ Circular operando com atraso" in avisos: mensagens.append("⚠️ Há atraso operacional informado.")
    if "🌧️ Tempo chuvoso, circular pode demorar mais do que o esperado" in avisos: mensagens.append("🌧️ Com chuva, o percurso pode levar mais tempo.")
    if "🚌 Rota alterada temporariamente" in avisos: mensagens.append("🚌 Há alteração temporária de rota.")
    if "🚪 Portão 1 fechado" in avisos: mensagens.append("🚪 Portão 1 fechado: o retorno deve ocorrer pelo Portão 2 e a volta tende a demorar mais.")
    if "🚪 Portão 2 fechado" in avisos: mensagens.append("🚪 Portão 2 fechado: o acesso deve ocorrer pelo Portão 1 e a volta tende a demorar mais.")
    return "\n".join(mensagens)


class Default(WorkerEntrypoint):
    def _estado(self):
        return self.env.BUS_STATE.getByName("principal")

    def _admin_ok(self, request):
        recebido = request.headers.get(HEADER_ADMIN)
        esperado = self.env.TELEGRAM_WEBHOOK_SECRET
        return bool(recebido and recebido == esperado)

    def _telegram_admin(self, telegram_id):
        try:
            esperado = str(self.env.ADMIN_TELEGRAM_ID).strip()
        except Exception:
            return False
        return bool(esperado and str(telegram_id) == esperado)

    async def _status_micro(self):
        return await self._estado().micro_status()

    async def _avisos_ativos(self):
        return (await self._estado().listar_avisos()).get("avisos", [])

    async def _menu(self, chat_id, telegram_id=None, boas_vindas=False):
        status = await self._status_micro()
        if boas_vindas:
            await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "👋 Bem-vindo ao BUSIVS!\n\nEm caso de dúvidas, clique em ❓ Ajuda ou fale com o administrador.")
        envio = await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "🚌 BUSIVS BOT\n\nEscolha uma opção:", reply_markup=teclado_menu(status.get("ativo"), self._telegram_admin(telegram_id)))
        avisos = await self._avisos_ativos()
        if avisos:
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, texto_avisos(avisos))
        return envio

    async def _onde(self, chat_id):
        principal = await self._estado().localizacao()
        texto = "🚌 <b>CIRCULAR PRINCIPAL</b>\n\n" + principal["texto"]
        avisos = await self._avisos_ativos()
        impacto = impacto_localizacao(avisos)
        if impacto:
            texto += "\n\n" + impacto
        status = await self._status_micro()
        if status.get("ativo"):
            micro = await self._estado().localizacao_micro()
            estado_micro = micro.get("estado") or {}
            texto_micro = micro.get("texto") if estado_micro.get("horario") and estado_micro.get("ponto_atual") else referencia_micro_sem_ponto()
            tempo = tempo_micro(status)
            texto += "\n\n────────────\n\n🚐 <b>MICRO — REFORÇO</b>" + ("\n" + tempo if tempo else "") + "\n\n" + texto_micro
        return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, texto, parse_mode="HTML", reply_markup=teclado_voltar())

    async def _local(self, chat_id):
        status = await self._status_micro()
        if status.get("ativo"):
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "📍 Qual veículo você viu?", reply_markup=teclado_veiculo())
        return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "📍 Onde o ônibus acabou de passar?", reply_markup=teclado_pontos("local_principal"))

    async def _horarios(self, chat_id):
        dados = await self._estado().resumo_horarios()
        texto = dados["texto"]
        status = await self._status_micro()
        if status.get("ativo"):
            texto = limitar_resumo_principal(texto, 2) + "\n\n" + resumo_micro()
            tempo = tempo_micro(status)
            if tempo: texto += "\n" + tempo
        return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, texto, parse_mode="HTML", reply_markup=teclado_voltar())

    async def _avisos(self, chat_id, telegram_id):
        if not self._telegram_admin(telegram_id):
            return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
        avisos = await self._avisos_ativos()
        status = await self._status_micro()
        return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, texto_avisos(avisos, True) + "\n\n🔐 Painel administrativo", reply_markup=teclado_admin_avisos(status.get("ativo")))

    async def _resultado_ponto(self, chat_id, resultado):
        if resultado.get("aceito"):
            texto = "Valeu! Registramos o ponto 😊"
        elif resultado.get("motivo") == "duplicado":
            texto = "Obrigado pela informação 😊"
        elif resultado.get("motivo") == "deslocamento_improvavel":
            texto = "⚠️ Essa confirmação parece incompatível com a última passagem registrada."
        elif resultado.get("motivo") == "ordem_rota_invalida":
            texto = "⚠️ Esse ponto não é compatível com a sequência atual do trajeto."
        elif resultado.get("motivo") in {"fora_circulacao", "micro_inativo"}:
            texto = "🚫 Não há percurso ativo para esse veículo no momento."
        else:
            texto = "⚠️ Não consegui reconhecer esse ponto."
        return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, texto, reply_markup=teclado_voltar())

    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao == "menu": return await self._menu(chat_id, telegram_id)
        if acao == "onde": return await self._onde(chat_id)
        if acao == "local": return await self._local(chat_id)
        if acao == "horarios": return await self._horarios(chat_id)
        if acao == "listar_horarios": return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "📋 Qual período você quer consultar?", reply_markup=teclado_periodos())
        if acao == "ajuda": return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "❓ Ajuda\n\nConsulte a rota ou releia as dicas de uso.\n\n👤 Administrador do BUSIVS\n📱 75 99978-0174", reply_markup=teclado_ajuda())
        if acao == "manual": return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, MANUAL, reply_markup=teclado_ajuda())
        if acao == "rota": return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, montar_rota_atual(), reply_markup=teclado_ajuda())
        if acao == "avisos": return await self._avisos(chat_id, telegram_id)
        if acao == "micro_ativo": return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
        if acao == "micro_confirmar": return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "🚐 Você viu o micro?", reply_markup=teclado_confirmar_micro())
        if acao == "micro_confirmar_sim":
            resultado = await self._estado().ativar_micro()
            if not resultado.get("ok") and resultado.get("motivo") == "fora_horario_micro":
                return await enviar_mensagem(
                    self.env.TELEGRAM_BOT_TOKEN,
                    chat_id,
                    "🚫 O micro não possui operação prevista neste horário.\n\nAs confirmações do reforço só são aceitas durante os blocos oficiais cadastrados.",
                    reply_markup=teclado_voltar(),
                )
            if resultado.get("ja_ativo"): return await self._menu(chat_id, telegram_id)
            texto = "🚐 Obrigado pela informação! O micro foi marcado como em operação.\n\n" + resumo_micro()
            tempo = tempo_micro(resultado)
            if tempo: texto += "\n" + tempo
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, texto, parse_mode="HTML", reply_markup=teclado_voltar())
        if acao == "micro_desativar":
            if not self._telegram_admin(telegram_id): return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            await self._estado().desativar_micro()
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "🚐 Micro desativado pelo administrador.", reply_markup=teclado_voltar())
        if acao == "veiculo_principal": return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "🚌 Onde o circular acabou de passar?", reply_markup=teclado_pontos("local_principal"))
        if acao == "veiculo_micro": return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "🚐 Onde o micro acabou de passar?", reply_markup=teclado_pontos("local_micro"))
        if acao.startswith("periodo_"):
            periodo = acao.replace("periodo_", "", 1)
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, listar_horarios_periodo(periodo), parse_mode="HTML", reply_markup=teclado_voltar())
        if acao.startswith("local_principal_"):
            return await self._resultado_ponto(chat_id, await self._estado().registrar(acao.replace("local_principal_", "", 1), telegram_id))
        if acao.startswith("local_micro_"):
            return await self._resultado_ponto(chat_id, await self._estado().registrar_micro(acao.replace("local_micro_", "", 1), telegram_id))
        if acao == "aviso_personalizado":
            if not self._telegram_admin(telegram_id): return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            await self._estado().iniciar_aviso_personalizado()
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "✏️ Envie agora a mensagem que deseja publicar como aviso.\n\nMáximo: 280 caracteres.")
        if acao.startswith("aviso_add_"):
            if not self._telegram_admin(telegram_id): return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            try: texto = AVISOS_PREDEFINIDOS[int(acao.replace("aviso_add_", "", 1))]
            except Exception: return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "⚠️ Aviso inválido.")
            resultado = await self._estado().adicionar_aviso(texto)
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, ("✅ Aviso ativado." if resultado.get("ok") else "⚠️ Não foi possível ativar.") + "\n\n" + texto_avisos(resultado.get("avisos", []), True), reply_markup=teclado_admin_avisos((await self._status_micro()).get("ativo")))
        if acao == "aviso_remover_menu":
            if not self._telegram_admin(telegram_id): return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            avisos = await self._avisos_ativos()
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "🗑️ Escolha o aviso:" if avisos else "📢 Não há avisos ativos.", reply_markup=teclado_remover_avisos(avisos) if avisos else teclado_admin_avisos((await self._status_micro()).get("ativo")))
        if acao.startswith("aviso_rem_"):
            if not self._telegram_admin(telegram_id): return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            resultado = await self._estado().remover_aviso(acao.replace("aviso_rem_", "", 1))
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "✅ Aviso removido.\n\n" + texto_avisos(resultado.get("avisos", []), True), reply_markup=teclado_admin_avisos((await self._status_micro()).get("ativo")))
        if acao == "aviso_limpar":
            if not self._telegram_admin(telegram_id): return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            await self._estado().limpar_avisos()
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "🧹 Todos os avisos foram removidos.", reply_markup=teclado_admin_avisos((await self._status_micro()).get("ativo")))
        return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "Use /start para abrir o menu do BUSIVS.", reply_markup=teclado_voltar())

    async def fetch(self, request):
        parsed = urlparse(request.url); caminho = parsed.path; method = request.method
        if method == "GET" and caminho == "/health":
            return Response.json({"status": "ok", "service": "busivs-bot", "runtime": "cloudflare-worker", "stage": "production-micro"})
        if method == "POST" and caminho == "/admin/telegram/set-webhook":
            if not self._admin_ok(request): return Response.json({"ok": False, "error": "admin_secret_invalid"}, status=403)
            url = f"{parsed.scheme}://{parsed.netloc}/telegram/webhook"
            r = await configurar_webhook(self.env.TELEGRAM_BOT_TOKEN, url, self.env.TELEGRAM_WEBHOOK_SECRET)
            return Response.json({"ok": r["ok_http"], "webhook_url": url}, status=200 if r["ok_http"] else 502)
        if method == "POST" and caminho == "/admin/telegram/delete-webhook":
            if not self._admin_ok(request): return Response.json({"ok": False, "error": "admin_secret_invalid"}, status=403)
            r = await remover_webhook(self.env.TELEGRAM_BOT_TOKEN)
            return Response.json({"ok": r["ok_http"]}, status=200 if r["ok_http"] else 502)
        if method == "POST" and caminho == "/telegram/webhook":
            segredo = request.headers.get(HEADER_SEGREDO_TELEGRAM)
            if not segredo or segredo != self.env.TELEGRAM_WEBHOOK_SECRET: return Response.json({"ok": False, "error": "webhook_secret_invalid"}, status=403)
            try: update = await request.json()
            except Exception: return Response.json({"ok": False, "error": "invalid_json"}, status=400)
            mensagem = update.get("message") or update.get("edited_message")
            if mensagem:
                chat_id = (mensagem.get("chat") or {}).get("id")
                usuario = (mensagem.get("from") or {}).get("id")
                if chat_id is None: return Response.json({"ok": True, "handled": False})
                texto = (mensagem.get("text") or "").strip()
                aguardando = await self._estado().aguardando_aviso_personalizado()
                if aguardando.get("ativo") and self._telegram_admin(usuario) and not texto.startswith("/"):
                    resultado = await self._estado().salvar_aviso_personalizado(texto)
                    envio = await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, ("✅ Aviso personalizado publicado." if resultado.get("ok") else "⚠️ Não consegui publicar esse aviso.") + "\n\n" + texto_avisos(resultado.get("avisos", []), True), reply_markup=teclado_admin_avisos((await self._status_micro()).get("ativo")))
                elif texto == "/start":
                    envio = await self._menu(chat_id, usuario, boas_vindas=True)
                else:
                    comandos = {"/onde": "onde", "/local": "local", "/rota": "rota", "/horarios": "horarios", "/listar_horarios": "listar_horarios"}
                    envio = await self._acao(comandos.get(texto, "desconhecido"), chat_id, usuario)
                return Response.json({"ok": envio["ok_http"], "handled": True}, status=200 if envio["ok_http"] else 502)
            callback = update.get("callback_query")
            if callback:
                cid = callback.get("id")
                if cid: await responder_callback(self.env.TELEGRAM_BOT_TOKEN, cid)
                chat_id = ((callback.get("message") or {}).get("chat") or {}).get("id")
                if chat_id is None: return Response.json({"ok": True, "handled": False})
                usuario = (callback.get("from") or {}).get("id")
                acao = callback.get("data") or ""
                envio = await self._acao(acao, chat_id, usuario)
                return Response.json({"ok": envio["ok_http"], "handled": True, "callback": acao}, status=200 if envio["ok_http"] else 502)
            return Response.json({"ok": True, "handled": False})
        return Response.json({"service": "BUSIVS BOT", "status": "cloudflare-running", "health": "/health", "webhook": "/telegram/webhook"})
