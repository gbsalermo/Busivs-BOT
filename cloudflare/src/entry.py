from urllib.parse import urlparse
from workers import Response, WorkerEntrypoint
from estado_bus import BusState
from dados import PONTOS, ROTULOS_PONTOS
from regras import listar_horarios_periodo, montar_resumo_horarios, montar_rota_atual
from telegram_api import configurar_webhook, enviar_mensagem, remover_webhook, responder_callback

HEADER_SEGREDO_TELEGRAM = "X-Telegram-Bot-Api-Secret-Token"
HEADER_ADMIN = "X-BUSIVS-Admin-Secret"

AVISOS_PREDEFINIDOS = [
    "🚪 Portão 1 fechado",
    "🚪 Portão 2 fechado",
    "⚠️ Circular operando com atraso",
    "🛠️ Circular temporariamente fora de operação",
    "🚌 Rota alterada temporariamente",
    "📅 Horários especiais hoje",
]


def teclado_menu():
    return {"inline_keyboard":[
        [{"text":"🚌 Onde está o ônibus?","callback_data":"onde"}],
        [{"text":"📍 Informar ponto atual","callback_data":"local"}],
        [{"text":"⏰ Próximos horários","callback_data":"horarios"}],
        [{"text":"📋 Listar horários","callback_data":"listar_horarios"}],
        [{"text":"🗺️ Rota atual","callback_data":"rota"}],
        [{"text":"📢 Avisos","callback_data":"avisos"}],
    ]}


def teclado_voltar():
    return {"inline_keyboard":[[{"text":"⬅️ Voltar ao menu","callback_data":"menu"}]]}


def teclado_periodos():
    return {"inline_keyboard":[
        [{"text":"🌅 Manhã","callback_data":"periodo_manha"},{"text":"🍽️ Almoço","callback_data":"periodo_meio_dia"}],
        [{"text":"🌤️ Tarde","callback_data":"periodo_tarde"},{"text":"🌙 Noite","callback_data":"periodo_noite"}],
        [{"text":"⬅️ Voltar ao menu","callback_data":"menu"}],
    ]}


def teclado_pontos():
    botoes=[]
    for pid,p in PONTOS.items():
        botoes.append({"text":ROTULOS_PONTOS.get(pid,p["nome"]),"callback_data":f"local_{pid}"})
    linhas=[botoes[i:i+2] for i in range(0,len(botoes),2)]
    linhas.append([{"text":"⬅️ Voltar ao menu","callback_data":"menu"}])
    return {"inline_keyboard":linhas}


def teclado_admin_avisos():
    linhas=[]
    for i,texto in enumerate(AVISOS_PREDEFINIDOS):
        linhas.append([{"text":texto,"callback_data":f"aviso_add_{i}"}])
    linhas += [
        [{"text":"🗑️ Remover aviso","callback_data":"aviso_remover_menu"}],
        [{"text":"🧹 Limpar todos","callback_data":"aviso_limpar"}],
        [{"text":"⬅️ Voltar ao menu","callback_data":"menu"}],
    ]
    return {"inline_keyboard":linhas}


def teclado_remover_avisos(avisos):
    linhas=[]
    for i,texto in enumerate(avisos):
        rotulo=texto if len(texto)<=45 else texto[:42]+"..."
        linhas.append([{"text":f"❌ {rotulo}","callback_data":f"aviso_rem_{i}"}])
    linhas.append([{"text":"⬅️ Voltar aos avisos","callback_data":"avisos"}])
    return {"inline_keyboard":linhas}


def texto_avisos(avisos):
    if not avisos:
        return "📢 Avisos\n\nNenhum aviso operacional ativo no momento."
    linhas=["📢 Avisos ativos",""]
    for aviso in avisos:
        linhas.append(f"• {aviso}")
    return "\n".join(linhas)


class Default(WorkerEntrypoint):
    def _estado(self):
        return self.env.BUS_STATE.getByName("principal")

    def _admin_ok(self, request):
        recebido=request.headers.get(HEADER_ADMIN)
        esperado=self.env.TELEGRAM_WEBHOOK_SECRET
        return bool(recebido and recebido==esperado)

    def _telegram_admin(self, telegram_id):
        try:
            esperado=str(self.env.ADMIN_TELEGRAM_ID).strip()
        except Exception:
            return False
        return bool(esperado and str(telegram_id)==esperado)

    async def _menu(self, chat_id):
        envio=await enviar_mensagem(
            self.env.TELEGRAM_BOT_TOKEN,
            chat_id,
            "🚌 BUSIVS BOT\n\nAcompanhe o circular da UFRB de forma colaborativa.\n\nEscolha uma opção:",
            reply_markup=teclado_menu(),
        )
        dados=await self._estado().listar_avisos()
        avisos=dados.get("avisos",[])
        if avisos:
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,texto_avisos(avisos))
        return envio

    async def _onde(self, chat_id):
        dados=await self._estado().localizacao()
        return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,dados["texto"],reply_markup=teclado_voltar())

    async def _local(self, chat_id):
        return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,"📍 Onde o ônibus acabou de passar?\n\nToque no ponto correspondente.",reply_markup=teclado_pontos())

    async def _horarios(self, chat_id):
        return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,montar_resumo_horarios(),parse_mode="HTML",reply_markup=teclado_voltar())

    async def _listar(self, chat_id):
        return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,"📋 Qual período você quer consultar?",reply_markup=teclado_periodos())

    async def _rota(self, chat_id):
        return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,montar_rota_atual(),reply_markup=teclado_voltar())

    async def _avisos(self, chat_id, telegram_id):
        if not self._telegram_admin(telegram_id):
            return {"ok_http":True,"status":200,"telegram":{"ok":True}}
        dados=await self._estado().listar_avisos()
        texto=texto_avisos(dados.get("avisos",[])) + "\n\n🔐 Painel administrativo\nEscolha um aviso pronto ou gerencie os ativos."
        return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,texto,reply_markup=teclado_admin_avisos())

    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao=="menu": return await self._menu(chat_id)
        if acao=="onde": return await self._onde(chat_id)
        if acao=="local": return await self._local(chat_id)
        if acao=="horarios": return await self._horarios(chat_id)
        if acao=="listar_horarios": return await self._listar(chat_id)
        if acao=="rota": return await self._rota(chat_id)
        if acao=="avisos": return await self._avisos(chat_id,telegram_id)

        if acao.startswith("aviso_add_"):
            if not self._telegram_admin(telegram_id):
                return {"ok_http":True,"status":200,"telegram":{"ok":True}}
            try:
                indice=int(acao.replace("aviso_add_","",1))
                texto=AVISOS_PREDEFINIDOS[indice]
            except Exception:
                return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,"⚠️ Aviso inválido.",reply_markup=teclado_admin_avisos())
            resultado=await self._estado().adicionar_aviso(texto)
            avisos=resultado.get("avisos",[])
            msg="✅ Aviso já estava ativo." if resultado.get("duplicado") else "✅ Aviso ativado."
            msg += "\n\n" + texto_avisos(avisos)
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,msg,reply_markup=teclado_admin_avisos())

        if acao=="aviso_remover_menu":
            if not self._telegram_admin(telegram_id):
                return {"ok_http":True,"status":200,"telegram":{"ok":True}}
            dados=await self._estado().listar_avisos(); avisos=dados.get("avisos",[])
            if not avisos:
                return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,"📢 Não há avisos ativos para remover.",reply_markup=teclado_admin_avisos())
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,"🗑️ Escolha o aviso que deseja remover:",reply_markup=teclado_remover_avisos(avisos))

        if acao.startswith("aviso_rem_"):
            if not self._telegram_admin(telegram_id):
                return {"ok_http":True,"status":200,"telegram":{"ok":True}}
            indice=acao.replace("aviso_rem_","",1)
            resultado=await self._estado().remover_aviso(indice)
            msg="✅ Aviso removido." if resultado.get("ok") else "⚠️ Não consegui remover esse aviso."
            msg += "\n\n" + texto_avisos(resultado.get("avisos",[]))
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,msg,reply_markup=teclado_admin_avisos())

        if acao=="aviso_limpar":
            if not self._telegram_admin(telegram_id):
                return {"ok_http":True,"status":200,"telegram":{"ok":True}}
            await self._estado().limpar_avisos()
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,"🧹 Todos os avisos foram removidos.",reply_markup=teclado_admin_avisos())

        if acao.startswith("periodo_"):
            periodo=acao.replace("periodo_","",1)
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,listar_horarios_periodo(periodo),parse_mode="HTML",reply_markup=teclado_voltar())

        if acao.startswith("local_"):
            ponto_id=acao.replace("local_","",1)
            resultado=await self._estado().registrar(ponto_id,telegram_id)
            if not resultado.get("aceito"):
                motivo=resultado.get("motivo")
                if motivo=="duplicado":
                    texto="Obrigado pela informação 😊"
                elif motivo=="fora_circulacao":
                    texto="🚫 Não há percurso ativo no momento.\n\n🚌 Pelo horário, o ônibus provavelmente está em %s."%resultado.get("origem","origem")
                    prox=resultado.get("proxima")
                    if prox: texto += f"\n⏰ Próxima saída prevista:\n     🕐 {prox['hora']} — {prox['origem']}"
                elif motivo=="deslocamento_improvavel":
                    texto=(
                        "⚠️ Essa confirmação parece incompatível com a última passagem registrada.\n\n"
                        "📍 O ônibus não teria tempo suficiente para chegar a esse ponto agora.\n"
                        "ℹ️ Aguarde um pouco ou confirme novamente quando ele realmente passar."
                    )
                else:
                    texto="⚠️ Não consegui reconhecer esse ponto."
            else:
                texto="Valeu! Registramos o ponto 😊"
            return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,texto,reply_markup=teclado_voltar())

        return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN,chat_id,"Use /start para abrir o menu do BUSIVS.",reply_markup=teclado_voltar())

    async def fetch(self, request):
        parsed=urlparse(request.url); caminho=parsed.path; method=request.method

        if method=="GET" and caminho=="/health":
            return Response.json({"status":"ok","service":"busivs-bot","runtime":"cloudflare-worker","stage":"avisos-alpha-1"})

        if method=="POST" and caminho=="/admin/telegram/set-webhook":
            if not self._admin_ok(request): return Response.json({"ok":False,"error":"admin_secret_invalid"},status=403)
            webhook_url=f"{parsed.scheme}://{parsed.netloc}/telegram/webhook"
            r=await configurar_webhook(self.env.TELEGRAM_BOT_TOKEN,webhook_url,self.env.TELEGRAM_WEBHOOK_SECRET)
            return Response.json({"ok":r["ok_http"],"webhook_url":webhook_url,"telegram_status":r["status"],"telegram_ok":bool(r["telegram"].get("ok"))},status=200 if r["ok_http"] else 502)

        if method=="POST" and caminho=="/admin/telegram/delete-webhook":
            if not self._admin_ok(request): return Response.json({"ok":False,"error":"admin_secret_invalid"},status=403)
            r=await remover_webhook(self.env.TELEGRAM_BOT_TOKEN)
            return Response.json({"ok":r["ok_http"],"telegram_status":r["status"],"telegram_ok":bool(r["telegram"].get("ok"))},status=200 if r["ok_http"] else 502)

        if method=="POST" and caminho=="/telegram/webhook":
            segredo=request.headers.get(HEADER_SEGREDO_TELEGRAM)
            if not segredo or segredo!=self.env.TELEGRAM_WEBHOOK_SECRET:
                return Response.json({"ok":False,"error":"webhook_secret_invalid"},status=403)
            try: update=await request.json()
            except Exception: return Response.json({"ok":False,"error":"invalid_json"},status=400)

            mensagem=update.get("message") or update.get("edited_message")
            if mensagem:
                chat_id=(mensagem.get("chat") or {}).get("id")
                if chat_id is None: return Response.json({"ok":True,"handled":False})
                texto=(mensagem.get("text") or "").strip()
                usuario=(mensagem.get("from") or {}).get("id")
                comandos={"/start":"menu","/onde":"onde","/local":"local","/rota":"rota","/horarios":"horarios","/listar_horarios":"listar_horarios"}
                envio=await self._acao(comandos.get(texto,"menu" if texto=="/start" else "desconhecido"),chat_id,usuario)
                return Response.json({"ok":envio["ok_http"],"handled":True},status=200 if envio["ok_http"] else 502)

            callback=update.get("callback_query")
            if callback:
                cid=callback.get("id")
                if cid: await responder_callback(self.env.TELEGRAM_BOT_TOKEN,cid)
                msg=callback.get("message") or {}; chat_id=(msg.get("chat") or {}).get("id")
                if chat_id is None:return Response.json({"ok":True,"handled":False})
                usuario=(callback.get("from") or {}).get("id"); acao=callback.get("data") or ""
                envio=await self._acao(acao,chat_id,usuario)
                return Response.json({"ok":envio["ok_http"],"handled":True,"callback":acao},status=200 if envio["ok_http"] else 502)

            return Response.json({"ok":True,"handled":False,"reason":"update_type_not_supported"})

        return Response.json({"service":"BUSIVS BOT","status":"cloudflare-running","health":"/health","webhook":"/telegram/webhook"})
