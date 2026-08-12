import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

BASE_DIR = Path(__file__).resolve().parent.parent
CLOUDFLARE_SRC = BASE_DIR / "cloudflare" / "src"
sys.path.insert(0, str(CLOUDFLARE_SRC))

from dados import PONTOS, ROTULOS_PONTOS
from regras import (
    agora_local,
    estado_vazio,
    listar_horarios_periodo,
    montar_localizacao,
    montar_resumo_horarios,
    montar_rota_atual,
    registrar_passagem,
)
from validacao_rota import validar_deslocamento
from estado_local import EstadoLocal

load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_TELEGRAM_ID = (os.getenv("ADMIN_TELEGRAM_ID") or "").strip()

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN nao configurado no .env")

ESTADO = EstadoLocal()

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


def admin_ok(user_id):
    return bool(ADMIN_TELEGRAM_ID and str(user_id) == ADMIN_TELEGRAM_ID)


def teclado_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚌 Onde está o ônibus?", callback_data="onde")],
        [InlineKeyboardButton("📍 Informar ponto atual", callback_data="local")],
        [InlineKeyboardButton("⏰ Próximos horários", callback_data="horarios")],
        [InlineKeyboardButton("📋 Listar horários", callback_data="listar_horarios")],
        [InlineKeyboardButton("🗺️ Rota atual", callback_data="rota")],
        [InlineKeyboardButton("📢 Avisos", callback_data="avisos")],
    ])


def teclado_voltar():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")]])


def teclado_periodos():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌅 Manhã", callback_data="periodo_manha"), InlineKeyboardButton("🍽️ Almoço", callback_data="periodo_meio_dia")],
        [InlineKeyboardButton("🌤️ Tarde", callback_data="periodo_tarde"), InlineKeyboardButton("🌙 Noite", callback_data="periodo_noite")],
        [InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")],
    ])


def teclado_pontos():
    botoes = [InlineKeyboardButton(ROTULOS_PONTOS.get(pid, p["nome"]), callback_data=f"local_{pid}") for pid, p in PONTOS.items()]
    linhas = [botoes[i:i + 2] for i in range(0, len(botoes), 2)]
    linhas.append([InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")])
    return InlineKeyboardMarkup(linhas)


def teclado_admin_avisos():
    linhas = [[InlineKeyboardButton(texto, callback_data=f"aviso_add_{i}")] for i, texto in enumerate(AVISOS_PREDEFINIDOS)]
    linhas += [
        [InlineKeyboardButton("✏️ Aviso personalizado", callback_data="aviso_personalizado")],
        [InlineKeyboardButton("🗑️ Remover aviso", callback_data="aviso_remover_menu")],
        [InlineKeyboardButton("🧹 Limpar todos", callback_data="aviso_limpar")],
        [InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(linhas)


def teclado_remover_avisos(avisos):
    linhas = []
    for i, texto in enumerate(avisos):
        rotulo = texto if len(texto) <= 45 else texto[:42] + "..."
        linhas.append([InlineKeyboardButton(f"❌ {rotulo}", callback_data=f"aviso_rem_{i}")])
    linhas.append([InlineKeyboardButton("⬅️ Voltar aos avisos", callback_data="avisos")])
    return InlineKeyboardMarkup(linhas)


def texto_avisos(avisos, contador=False):
    sufixo = f" ({len(avisos)}/3)" if contador else ""
    if not avisos:
        return f"📢 Avisos{sufixo}\n\nNenhum aviso operacional ativo no momento."
    return "\n".join([f"📢 Avisos ativos{sufixo}", ""] + [f"• {a}" for a in avisos])


def impacto_localizacao(avisos):
    if "🛠️ Circular temporariamente fora de operação" in avisos:
        return "🚨 O circular foi informado como temporariamente fora de operação. A última localização não garante que o veículo continue em movimento."
    if "🛠️ Circular quebrou em meio ao trajeto" in avisos:
        return "🚨 Há aviso de quebra durante o trajeto. A volta atual pode não ser concluída e a última confirmação pode representar apenas o ponto onde a operação foi interrompida."
    mensagens = []
    if "⚠️ Circular operando com atraso" in avisos:
        mensagens.append("⚠️ Há atraso operacional informado; posição e previsões podem estar deslocadas em relação ao horário oficial.")
    if "🌧️ Tempo chuvoso, circular pode demorar mais do que o esperado" in avisos:
        mensagens.append("🌧️ Com chuva, o percurso pode levar mais tempo que o estimado.")
    if "🚌 Rota alterada temporariamente" in avisos:
        mensagens.append("🚌 Há alteração temporária de rota; o próximo ponto previsto pode não seguir a rota padrão.")
    if "🚪 Portão 1 fechado" in avisos:
        mensagens.append("🚪 Portão 1 fechado: o ponto continua sendo atendido, mas o retorno deve ocorrer pelo Portão 2 e a volta tende a demorar mais.")
    if "🚪 Portão 2 fechado" in avisos:
        mensagens.append("🚪 Portão 2 fechado: o ponto continua sendo atendido, mas o acesso deve ocorrer pelo Portão 1 e a volta tende a demorar mais.")
    return "\n".join(mensagens)


def impacto_horarios(avisos):
    mensagens = []
    if "🛠️ Circular temporariamente fora de operação" in avisos:
        mensagens.append("🚨 O circular está informado como temporariamente fora de operação. As próximas saídas podem não ocorrer até a normalização.")
    if "🛠️ Circular quebrou em meio ao trajeto" in avisos:
        mensagens.append("🚨 A volta em andamento foi prejudicada por uma quebra. Ela pode não ser concluída e as próximas saídas também podem sofrer atraso ou cancelamento.")
    if "⚠️ Circular operando com atraso" in avisos:
        mensagens.append("⚠️ Os horários abaixo são oficiais, mas há atraso operacional informado.")
    if "🌧️ Tempo chuvoso, circular pode demorar mais do que o esperado" in avisos:
        mensagens.append("🌧️ O tempo chuvoso pode aumentar a duração das voltas e afetar os horários seguintes.")
    if "🚪 Portão 1 fechado" in avisos or "🚪 Portão 2 fechado" in avisos:
        mensagens.append("🚪 O fechamento de portão aumenta o percurso e pode impactar horários posteriores.")
    return "\n".join(mensagens)


async def enviar_menu(mensagem):
    await mensagem.reply_text("🚌 BUSIVS BOT — ALPHA LOCAL\n\nEscolha uma opção:", reply_markup=teclado_menu())
    avisos = ESTADO.listar_avisos()
    if avisos:
        await mensagem.reply_text(texto_avisos(avisos))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message:
        await enviar_menu(update.effective_message)


async def texto_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user or not admin_ok(update.effective_user.id):
        return
    if not ESTADO.aguardando_aviso_personalizado():
        return
    texto = (update.effective_message.text or "").strip()
    if texto in {"/cancelar", "/cancel"}:
        ESTADO.cancelar_aviso_personalizado()
        await update.effective_message.reply_text("❌ Criação de aviso personalizado cancelada.", reply_markup=teclado_admin_avisos())
        return
    if texto.startswith("/"):
        return
    resultado = ESTADO.salvar_aviso_personalizado(texto)
    avisos = resultado.get("avisos", [])
    if resultado.get("ok"):
        msg = "✅ Aviso personalizado publicado."
    elif resultado.get("motivo") == "limite_atingido":
        msg = "⚠️ Limite de 3 avisos ativos atingido."
    elif resultado.get("motivo") == "aviso_muito_longo":
        msg = "⚠️ O aviso deve ter no máximo 280 caracteres."
    else:
        msg = "⚠️ Não consegui publicar o aviso."
    await update.effective_message.reply_text(msg + "\n\n" + texto_avisos(avisos, True), reply_markup=teclado_admin_avisos())


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    acao = query.data or ""
    user_id = update.effective_user.id if update.effective_user else None
    chat = query.message

    if acao == "menu":
        await enviar_menu(chat); return
    if acao == "onde":
        estado = ESTADO.obter_estado(estado_vazio)
        estado, texto = montar_localizacao(estado)
        ESTADO.salvar_estado(estado)
        impacto = impacto_localizacao(ESTADO.listar_avisos())
        if impacto: texto += "\n\n" + impacto
        await chat.reply_text(texto, reply_markup=teclado_voltar()); return
    if acao == "local":
        await chat.reply_text("📍 Onde o ônibus acabou de passar?\n\nToque no ponto correspondente.", reply_markup=teclado_pontos()); return
    if acao.startswith("local_"):
        ponto_id = acao.replace("local_", "", 1)
        estado = ESTADO.obter_estado(estado_vazio)
        agora = agora_local()
        bloqueio = validar_deslocamento(estado, ponto_id, agora, ESTADO.listar_avisos())
        if bloqueio is not None:
            resultado = bloqueio
        else:
            estado, resultado = registrar_passagem(estado, ponto_id, user_id, agora=agora)
            ESTADO.salvar_estado(estado)
        if resultado.get("aceito"):
            texto = "Valeu! Registramos o ponto 😊"
        elif resultado.get("motivo") == "duplicado":
            texto = "Obrigado pela informação 😊"
        elif resultado.get("motivo") == "deslocamento_improvavel":
            texto = "⚠️ Essa confirmação parece incompatível com a última passagem registrada.\n\n📍 O ônibus não teria tempo suficiente para chegar a esse ponto agora."
        elif resultado.get("motivo") == "fora_circulacao":
            texto = "🚫 Não há percurso ativo no momento."
        else:
            texto = "⚠️ Não consegui reconhecer esse ponto."
        await chat.reply_text(texto, reply_markup=teclado_voltar()); return
    if acao == "horarios":
        texto = montar_resumo_horarios()
        impacto = impacto_horarios(ESTADO.listar_avisos())
        if impacto: texto += "\n\n<b>⚠️ Situação operacional</b>\n" + impacto
        await chat.reply_text(texto, parse_mode="HTML", reply_markup=teclado_voltar()); return
    if acao == "listar_horarios":
        await chat.reply_text("📋 Qual período você quer consultar?", reply_markup=teclado_periodos()); return
    if acao.startswith("periodo_"):
        periodo = acao.replace("periodo_", "", 1)
        texto = listar_horarios_periodo(periodo)
        impacto = impacto_horarios(ESTADO.listar_avisos())
        if impacto: texto += "\n\n<b>⚠️ Situação operacional</b>\n" + impacto
        await chat.reply_text(texto, parse_mode="HTML", reply_markup=teclado_voltar()); return
    if acao == "rota":
        await chat.reply_text(montar_rota_atual(), reply_markup=teclado_voltar()); return
    if acao == "avisos":
        if not admin_ok(user_id): return
        avisos = ESTADO.listar_avisos()
        await chat.reply_text(texto_avisos(avisos, True) + "\n\n🔐 Painel administrativo", reply_markup=teclado_admin_avisos()); return
    if acao == "aviso_personalizado":
        if not admin_ok(user_id): return
        if len(ESTADO.listar_avisos()) >= 3:
            await chat.reply_text("⚠️ Já existem 3/3 avisos ativos. Remova um antes de criar outro.", reply_markup=teclado_admin_avisos()); return
        ESTADO.iniciar_aviso_personalizado()
        await chat.reply_text("✏️ Envie agora a mensagem que deseja publicar como aviso.\n\nMáximo: 280 caracteres.\nDigite /cancelar para sair."); return
    if acao.startswith("aviso_add_"):
        if not admin_ok(user_id): return
        try: texto = AVISOS_PREDEFINIDOS[int(acao.replace("aviso_add_", "", 1))]
        except Exception: return
        resultado = ESTADO.adicionar_aviso(texto)
        msg = "✅ Aviso ativado." if resultado.get("ok") and not resultado.get("duplicado") else "✅ Esse aviso já estava ativo." if resultado.get("duplicado") else "⚠️ Limite de 3 avisos ativos atingido."
        await chat.reply_text(msg + "\n\n" + texto_avisos(resultado.get("avisos", []), True), reply_markup=teclado_admin_avisos()); return
    if acao == "aviso_remover_menu":
        if not admin_ok(user_id): return
        avisos = ESTADO.listar_avisos()
        if not avisos:
            await chat.reply_text("📢 Não há avisos ativos para remover.", reply_markup=teclado_admin_avisos()); return
        await chat.reply_text("🗑️ Escolha o aviso que deseja remover:", reply_markup=teclado_remover_avisos(avisos)); return
    if acao.startswith("aviso_rem_"):
        if not admin_ok(user_id): return
        resultado = ESTADO.remover_aviso(acao.replace("aviso_rem_", "", 1))
        await chat.reply_text(("✅ Aviso removido." if resultado.get("ok") else "⚠️ Aviso inválido.") + "\n\n" + texto_avisos(resultado.get("avisos", []), True), reply_markup=teclado_admin_avisos()); return
    if acao == "aviso_limpar":
        if not admin_ok(user_id): return
        ESTADO.limpar_avisos()
        await chat.reply_text("🧹 Todos os avisos foram removidos.", reply_markup=teclado_admin_avisos()); return


async def erro(update, context):
    print("ERRO:", repr(context.error))


def main():
    print("BUSIVS ALPHA LOCAL iniciado por polling.")
    print("Ctrl+C para encerrar.")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto_admin))
    app.add_error_handler(erro)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
