import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

BASE_DIR = Path(__file__).resolve().parent.parent
CLOUDFLARE_SRC = BASE_DIR / "cloudflare" / "src"
sys.path.insert(0, str(CLOUDFLARE_SRC))

from dados import PONTOS, ROTULOS_PONTOS
from regras import agora_local, estado_vazio, listar_horarios_periodo, montar_localizacao, montar_resumo_horarios, montar_rota_atual, registrar_passagem
from validacao_rota import validar_deslocamento
from estado_local import EstadoLocal
from micro import proxima_volta_micro, resumo_micro, volta_micro_atual

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

MANUAL = """📖 Dicas para uso do BUSIVS

🚌 Onde está o ônibus?
Mostra a última confirmação colaborativa e a estimativa do trajeto. Se o micro estiver ativo, os dois veículos aparecem separados.

📍 Informar ponto atual
Use somente quando você acabou de ver o veículo passar. Se o micro estiver ativo, escolha primeiro qual veículo você viu.

⏰ Próximos horários
Mostra as próximas referências do circular principal. Quando o micro estiver em operação, também exibe a referência do reforço.

📋 Listar horários
Consulta os horários oficiais do circular principal por período.

🚐 Confirmar que micro está rodando
Use somente quando você realmente vir o micro-ônibus de reforço operando. Depois de confirmado, o botão ficará verde e não precisará ser confirmado novamente.

📢 Avisos operacionais
Quando houver alguma ocorrência importante, os avisos aparecem automaticamente no bot.

❗ As localizações são colaborativas e os horários são referências oficiais. Atrasos e alterações podem acontecer.
🤝 Informe pontos apenas quando realmente tiver visto o veículo.

👤 Administrador do BUSIVS
📱 75 99978-0174"""


def admin_ok(uid):
    return bool(ADMIN_TELEGRAM_ID and str(uid) == ADMIN_TELEGRAM_ID)


def limitar_resumo_principal(texto, quantidade=2):
    linhas = texto.splitlines()
    marcador = f"<b>{quantidade + 1}ª volta</b>"
    inicio = next((i for i, linha in enumerate(linhas) if marcador in linha), None)
    if inicio is None:
        return texto
    rodape = next(
        (
            i
            for i in range(inicio, len(linhas))
            if linhas[i].startswith("⚠️ <b>Horários de pico</b>")
            or linhas[i].startswith("ℹ️ Horários do Portão 1")
        ),
        None,
    )
    if rodape is None:
        return "\n".join(linhas[:inicio]).rstrip()
    return "\n".join(linhas[:inicio] + linhas[rodape:]).strip()


def texto_tempo_micro():
    ativado_em = ESTADO.dados.get("micro_ativado_em")
    if not ativado_em:
        return ""
    try:
        inicio = datetime.fromisoformat(ativado_em)
        minutos = max(0, int((agora_local() - inicio).total_seconds() // 60))
    except Exception:
        return ""
    if minutos < 1:
        return "🕐 Operação confirmada agora."
    if minutos == 1:
        return "🕐 Operação confirmada há 1 min."
    return f"🕐 Operação confirmada há {minutos} min."


def resumo_micro_status():
    status = texto_tempo_micro()
    base = resumo_micro()
    return base + ("\n" + status if status else "")


def montar_localizacao_micro(estado):
    if estado.get("horario") and estado.get("ponto_atual"):
        return montar_localizacao(estado)

    atual = volta_micro_atual()
    proxima = proxima_volta_micro()
    linhas = ["⚪ Sem confirmação de ponto recente."]
    if atual:
        linhas += [
            "",
            "🔵 <b>Referência atual do micro</b>",
            f"🕐 <b>{atual['inicio'].strftime('%H:%M')}</b> — {atual['origem']}",
        ]
    if proxima:
        linhas += [
            "",
            "🟢 <b>Próxima referência</b>",
            f"🕐 <b>{proxima['inicio'].strftime('%H:%M')}</b> — {proxima['origem']}",
        ]
    if not atual and not proxima:
        linhas += ["", "ℹ️ Não há referência de horário cadastrada para o micro neste momento."]
    return estado, "\n".join(linhas)


def teclado_menu(uid=None):
    micro_ativo = ESTADO.micro_esta_ativo()
    rotulo_micro = "🚐 Micro em operação ✅" if micro_ativo else "🚐 Confirmar que micro está rodando"
    callback_micro = "micro_ativo" if micro_ativo else "micro_confirmar"

    linhas = [
        [InlineKeyboardButton("🚌 Onde está o ônibus?", callback_data="onde")],
        [InlineKeyboardButton("📍 Informar ponto atual", callback_data="local")],
        [InlineKeyboardButton("⏰ Próximos horários", callback_data="horarios")],
        [InlineKeyboardButton("📋 Listar horários", callback_data="listar_horarios")],
        [InlineKeyboardButton(rotulo_micro, callback_data=callback_micro)],
    ]
    if admin_ok(uid):
        linhas.append([InlineKeyboardButton("📢 Avisos", callback_data="avisos")])
    linhas.append([InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")])
    return InlineKeyboardMarkup(linhas)


def teclado_confirmar_micro():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Sim, está rodando", callback_data="micro_confirmar_sim")],
        [InlineKeyboardButton("❌ Voltar", callback_data="menu")],
    ])


def teclado_voltar():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")]])


def teclado_ajuda():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗺️ Rota atual", callback_data="rota")],
        [InlineKeyboardButton("📖 Dicas para uso do BOT", callback_data="manual")],
        [InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")],
    ])


def teclado_periodos():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌅 Manhã", callback_data="periodo_manha"), InlineKeyboardButton("🍽️ Almoço", callback_data="periodo_meio_dia")],
        [InlineKeyboardButton("🌤️ Tarde", callback_data="periodo_tarde"), InlineKeyboardButton("🌙 Noite", callback_data="periodo_noite")],
        [InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")],
    ])


def teclado_pontos(prefixo):
    botoes = [InlineKeyboardButton(ROTULOS_PONTOS.get(pid, p["nome"]), callback_data=f"{prefixo}_{pid}") for pid, p in PONTOS.items()]
    linhas = [botoes[i:i + 2] for i in range(0, len(botoes), 2)]
    linhas.append([InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")])
    return InlineKeyboardMarkup(linhas)


def teclado_veiculo():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚌 Circular principal", callback_data="veiculo_principal")],
        [InlineKeyboardButton("🚐 Micro — reforço", callback_data="veiculo_micro")],
        [InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")],
    ])


def teclado_admin_avisos():
    linhas = [[InlineKeyboardButton(texto, callback_data=f"aviso_add_{i}")] for i, texto in enumerate(AVISOS_PREDEFINIDOS)]
    linhas += [
        [InlineKeyboardButton("✏️ Aviso personalizado", callback_data="aviso_personalizado")],
        [InlineKeyboardButton("🗑️ Remover aviso", callback_data="aviso_remover_menu")],
        [InlineKeyboardButton("🧹 Limpar todos", callback_data="aviso_limpar")],
    ]
    if ESTADO.micro_esta_ativo():
        linhas.append([InlineKeyboardButton("🚐 Desativar micro", callback_data="micro_desativar")])
    linhas.append([InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")])
    return InlineKeyboardMarkup(linhas)


def teclado_remover_avisos(avisos):
    linhas = [[InlineKeyboardButton("❌ " + texto[:45], callback_data=f"aviso_rem_{i}")] for i, texto in enumerate(avisos)]
    linhas.append([InlineKeyboardButton("⬅️ Voltar aos avisos", callback_data="avisos")])
    return InlineKeyboardMarkup(linhas)


def texto_avisos(avisos, contador=False):
    sufixo = f" ({len(avisos)}/3)" if contador else ""
    if not avisos:
        return f"📢 Avisos{sufixo}\n\nNenhum aviso operacional ativo no momento."
    return "\n".join([f"📢 Avisos ativos{sufixo}", ""] + [f"• {aviso}" for aviso in avisos])


async def enviar_menu(mensagem, uid=None):
    await mensagem.reply_text("🚌 BUSIVS BOT — ALPHA LOCAL\n\nEscolha uma opção:", reply_markup=teclado_menu(uid))
    avisos = ESTADO.listar_avisos()
    if avisos:
        await mensagem.reply_text(texto_avisos(avisos))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "👋 Bem-vindo ao BUSIVS!\n\nEm caso de dúvidas, clique em ❓ Ajuda ou fale com o administrador."
    )
    await enviar_menu(update.effective_message, update.effective_user.id if update.effective_user else None)


async def texto_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user or not admin_ok(update.effective_user.id) or not ESTADO.aguardando_aviso_personalizado():
        return
    texto = (update.effective_message.text or "").strip()
    if texto in {"/cancelar", "/cancel"}:
        ESTADO.cancelar_aviso_personalizado()
        await update.effective_message.reply_text("❌ Criação cancelada.", reply_markup=teclado_admin_avisos())
        return
    resultado = ESTADO.salvar_aviso_personalizado(texto)
    await update.effective_message.reply_text(
        ("✅ Aviso publicado." if resultado.get("ok") else "⚠️ Não consegui publicar.") + "\n\n" + texto_avisos(resultado.get("avisos", []), True),
        reply_markup=teclado_admin_avisos(),
    )


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    acao = query.data or ""
    uid = update.effective_user.id if update.effective_user else None
    mensagem = query.message

    if acao == "menu":
        await enviar_menu(mensagem, uid)
        return
    if acao == "ajuda":
        await mensagem.reply_text(
            "❓ Ajuda\n\nConsulte a rota ou releia as dicas de uso.\n\n👤 Administrador do BUSIVS\n📱 75 99978-0174",
            reply_markup=teclado_ajuda(),
        )
        return
    if acao == "manual":
        await mensagem.reply_text(MANUAL, reply_markup=teclado_ajuda())
        return
    if acao == "rota":
        await mensagem.reply_text(montar_rota_atual(), reply_markup=teclado_ajuda())
        return
    if acao == "micro_ativo":
        return
    if acao == "micro_confirmar":
        await mensagem.reply_text("🚐 Você viu o micro?", reply_markup=teclado_confirmar_micro())
        return
    if acao == "micro_confirmar_sim":
        resultado = ESTADO.ativar_micro()
        if resultado.get("ja_ativo"):
            await enviar_menu(mensagem, uid)
            return
        await mensagem.reply_text(
            "🚐 Obrigado pela informação! O micro foi marcado como em operação.\n\n" + resumo_micro_status(),
            parse_mode="HTML",
            reply_markup=teclado_voltar(),
        )
        return
    if acao == "micro_desativar":
        if admin_ok(uid):
            ESTADO.desativar_micro()
            await mensagem.reply_text("🚐 Micro desativado pelo administrador.", reply_markup=teclado_admin_avisos())
        return
    if acao == "onde":
        estado = ESTADO.obter_estado(estado_vazio)
        estado, texto = montar_localizacao(estado)
        ESTADO.salvar_estado(estado)
        texto = "🚌 <b>CIRCULAR PRINCIPAL</b>\n\n" + texto
        if ESTADO.micro_esta_ativo():
            estado_micro = ESTADO.obter_estado(estado_vazio, "micro")
            estado_micro, texto_micro = montar_localizacao_micro(estado_micro)
            ESTADO.salvar_estado(estado_micro, "micro")
            status = texto_tempo_micro()
            texto += "\n\n────────────\n\n🚐 <b>MICRO — REFORÇO</b>" + ("\n" + status if status else "") + "\n\n" + texto_micro
        await mensagem.reply_text(texto, parse_mode="HTML", reply_markup=teclado_voltar())
        return
    if acao == "local":
        if ESTADO.micro_esta_ativo():
            await mensagem.reply_text("📍 Qual veículo você viu?", reply_markup=teclado_veiculo())
        else:
            await mensagem.reply_text("📍 Onde o ônibus acabou de passar?", reply_markup=teclado_pontos("local_principal"))
        return
    if acao == "veiculo_principal":
        await mensagem.reply_text("🚌 Onde o circular acabou de passar?", reply_markup=teclado_pontos("local_principal"))
        return
    if acao == "veiculo_micro":
        await mensagem.reply_text("🚐 Onde o micro acabou de passar?", reply_markup=teclado_pontos("local_micro"))
        return
    if acao.startswith("local_principal_") or acao.startswith("local_micro_"):
        veiculo = "micro" if acao.startswith("local_micro_") else "principal"
        ponto = acao.replace(f"local_{veiculo}_", "", 1)
        estado = ESTADO.obter_estado(estado_vazio, veiculo)
        agora = agora_local()
        bloqueio = validar_deslocamento(estado, ponto, agora, ESTADO.listar_avisos())
        resultado = bloqueio
        if resultado is None:
            estado, resultado = registrar_passagem(estado, ponto, uid, agora=agora)
            ESTADO.salvar_estado(estado, veiculo)
        texto = "Valeu! Registramos o ponto 😊" if resultado.get("aceito") else "Obrigado pela informação 😊" if resultado.get("motivo") == "duplicado" else "⚠️ Não foi possível registrar esta confirmação."
        await mensagem.reply_text(texto, reply_markup=teclado_voltar())
        return
    if acao == "horarios":
        micro_ativo = ESTADO.micro_esta_ativo()
        texto = montar_resumo_horarios()
        if micro_ativo:
            texto = limitar_resumo_principal(texto, 2) + "\n\n" + resumo_micro_status()
        await mensagem.reply_text(texto, parse_mode="HTML", reply_markup=teclado_voltar())
        return
    if acao == "listar_horarios":
        await mensagem.reply_text("📋 Qual período você quer consultar?", reply_markup=teclado_periodos())
        return
    if acao.startswith("periodo_"):
        await mensagem.reply_text(listar_horarios_periodo(acao.replace("periodo_", "", 1)), parse_mode="HTML", reply_markup=teclado_voltar())
        return
    if acao == "avisos":
        if not admin_ok(uid):
            return
        avisos = ESTADO.listar_avisos()
        await mensagem.reply_text(texto_avisos(avisos, True) + "\n\n🔐 Painel administrativo", reply_markup=teclado_admin_avisos())
        return
    if acao == "aviso_personalizado":
        if admin_ok(uid):
            ESTADO.iniciar_aviso_personalizado()
            await mensagem.reply_text("✏️ Envie a mensagem do aviso. Máximo 280 caracteres. /cancelar para sair.")
        return
    if acao.startswith("aviso_add_"):
        if not admin_ok(uid):
            return
        try:
            texto = AVISOS_PREDEFINIDOS[int(acao.replace("aviso_add_", "", 1))]
        except Exception:
            return
        resultado = ESTADO.adicionar_aviso(texto)
        await mensagem.reply_text(
            ("✅ Aviso ativado." if resultado.get("ok") else "⚠️ Não foi possível ativar.") + "\n\n" + texto_avisos(resultado.get("avisos", []), True),
            reply_markup=teclado_admin_avisos(),
        )
        return
    if acao == "aviso_remover_menu":
        if not admin_ok(uid):
            return
        avisos = ESTADO.listar_avisos()
        await mensagem.reply_text("🗑️ Escolha o aviso:" if avisos else "📢 Não há avisos ativos.", reply_markup=teclado_remover_avisos(avisos) if avisos else teclado_admin_avisos())
        return
    if acao.startswith("aviso_rem_"):
        if not admin_ok(uid):
            return
        resultado = ESTADO.remover_aviso(acao.replace("aviso_rem_", "", 1))
        await mensagem.reply_text("✅ Aviso removido.\n\n" + texto_avisos(resultado.get("avisos", []), True), reply_markup=teclado_admin_avisos())
        return
    if acao == "aviso_limpar":
        if admin_ok(uid):
            ESTADO.limpar_avisos()
            await mensagem.reply_text("🧹 Todos os avisos foram removidos.", reply_markup=teclado_admin_avisos())


def main():
    print("BUSIVS ALPHA LOCAL iniciado por polling.")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto_admin))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
