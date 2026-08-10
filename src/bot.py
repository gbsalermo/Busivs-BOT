import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, validar_configuracao
from horarios import listar_horarios_periodo, montar_resumo_horarios
from passagens import montar_localizacao_atual, registrar_passagem
from rota import carregar_pontos, carregar_rota

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


ROTULOS_PONTOS = {
    "ru": "RU / Residências",
    "fitotecnia": "Fitotecnia",
    "solos_neas_florestal": "Solos / NEAS / Florestal",
    "pavilhao_1": "Pavilhão I",
    "biblioteca": "Biblioteca",
    "pavilhao_2": "Pavilhão II",
    "pavilhao_engenharia": "Pav. Engenharia",
    "portao_2": "Portão 2",
    "ponto_externo_1": "Ponto Externo I / Alex",
    "ponto_externo_2": "Ponto Externo II / Canãa",
    "portao_1": "Portão 1",
    "torre_cotec": "Torre / COTEC",
}


def teclado_menu_principal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚌 Onde está o ônibus?", callback_data="onde")],
            [InlineKeyboardButton("📍 Informar passagem", callback_data="local")],
            [InlineKeyboardButton("⏰ Próximos horários", callback_data="horarios")],
            [InlineKeyboardButton("📋 Listar horários", callback_data="listar_horarios")],
            [InlineKeyboardButton("🗺️ Rota atual", callback_data="rota")],
            [InlineKeyboardButton("📢 Avisos", callback_data="avisos")],
        ]
    )


def teclado_voltar_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")]]
    )


def teclado_periodos() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🌅 Manhã", callback_data="periodo_manha"),
                InlineKeyboardButton("🍽️ Almoço", callback_data="periodo_meio_dia"),
            ],
            [
                InlineKeyboardButton("🌤️ Tarde", callback_data="periodo_tarde"),
                InlineKeyboardButton("🌙 Noite", callback_data="periodo_noite"),
            ],
            [InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")],
        ]
    )


def teclado_pontos() -> InlineKeyboardMarkup:
    pontos = carregar_pontos()
    botoes = []

    for ponto_id in pontos:
        rotulo = ROTULOS_PONTOS.get(ponto_id, pontos[ponto_id]["nome"])
        botoes.append(
            InlineKeyboardButton(rotulo, callback_data=f"local_{ponto_id}")
        )

    linhas = [botoes[i : i + 2] for i in range(0, len(botoes), 2)]
    linhas.append([InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")])
    return InlineKeyboardMarkup(linhas)


def montar_rota_atual() -> str:
    rota = carregar_rota()
    pontos = carregar_pontos()

    linhas = [
        "🗺️ ROTA PRINCIPAL",
        "",
        "➡️ Saída em direção à Rua",
        "",
    ]

    for indice, item in enumerate(rota):
        ponto = pontos[item["ponto_id"]]
        nome = ROTULOS_PONTOS.get(ponto["id"], ponto["nome"])
        opcional = item.get("opcional", ponto.get("opcional", False))

        if opcional:
            nome = f"{nome} (opcional)"

        linhas.append(f"{indice + 1}. {nome}")

        if item["ponto_id"] == "ponto_externo_2":
            linhas.extend(["", "⬅️ Retorno em direção ao RU", ""])

    linhas.extend(
        [
            "",
            "ℹ️ Pontos opcionais só são atendidos quando houver desembarque.",
        ]
    )

    return "\n".join(linhas)


async def enviar_menu(mensagem) -> None:
    await mensagem.reply_text(
        "🚌 BUSIVS BOT\n\n"
        "Acompanhe o circular da UFRB de forma colaborativa.\n\n"
        "Escolha uma opção:",
        reply_markup=teclado_menu_principal(),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensagem = update.effective_message
    if mensagem is None:
        return

    await enviar_menu(mensagem)


async def botao_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await enviar_menu(query.message)


async def onde(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensagem = update.effective_message
    if mensagem:
        await mensagem.reply_text(
            montar_localizacao_atual(),
            reply_markup=teclado_voltar_menu(),
        )


async def botao_onde(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        montar_localizacao_atual(),
        reply_markup=teclado_voltar_menu(),
    )


async def local(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensagem = update.effective_message
    if mensagem:
        await mensagem.reply_text(
            "📍 Onde o ônibus acabou de passar?\n\n"
            "Toque no ponto correspondente.",
            reply_markup=teclado_pontos(),
        )


async def botao_local(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📍 Onde o ônibus acabou de passar?\n\n"
        "Toque no ponto correspondente.",
        reply_markup=teclado_pontos(),
    )


async def botao_registrar_ponto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    ponto_id = query.data.replace("local_", "", 1)
    usuario = update.effective_user
    telegram_id = usuario.id if usuario else None

    resultado = registrar_passagem(ponto_id, telegram_id)

    if not resultado["aceito"]:
        if resultado["motivo"] == "duplicado":
            await query.message.reply_text(
                "Obrigado pela informação 😊",
                reply_markup=teclado_voltar_menu(),
            )
            return

        if resultado["motivo"] == "fora_circulacao":
            proxima = resultado.get("proxima")
            origem = resultado.get("origem", "origem")

            linhas = [
                "🚫 Não há percurso ativo no momento.",
                "",
                f"🚌 Pelo horário, o ônibus provavelmente está em {origem}.",
            ]

            if proxima is not None:
                linhas.extend(
                    [
                        "⏰ Próxima saída prevista:",
                        f"     🕐 {proxima['hora']} — {proxima['origem']}",
                    ]
                )

            await query.message.reply_text(
                "\n".join(linhas),
                reply_markup=teclado_voltar_menu(),
            )
            return

        await query.message.reply_text(
            "⚠️ Não consegui reconhecer esse ponto.",
            reply_markup=teclado_voltar_menu(),
        )
        return

    await query.message.reply_text(
        "Valeu! Registramos o ponto 😊",
        reply_markup=teclado_voltar_menu(),
    )


async def rota_atual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensagem = update.effective_message
    if mensagem:
        await mensagem.reply_text(
            montar_rota_atual(),
            reply_markup=teclado_voltar_menu(),
        )


async def botao_rota(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        montar_rota_atual(),
        reply_markup=teclado_voltar_menu(),
    )


async def horarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensagem = update.effective_message
    if mensagem:
        await mensagem.reply_text(
            montar_resumo_horarios("principal"),
            parse_mode="HTML",
            reply_markup=teclado_voltar_menu(),
        )


async def comando_listar_horarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensagem = update.effective_message
    if mensagem:
        await mensagem.reply_text(
            "📋 Qual período você quer consultar?",
            reply_markup=teclado_periodos(),
        )


async def botao_horarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        montar_resumo_horarios("principal"),
        parse_mode="HTML",
        reply_markup=teclado_voltar_menu(),
    )


async def botao_listar_horarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📋 Qual período você quer consultar?",
        reply_markup=teclado_periodos(),
    )


async def botao_periodo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    periodo = query.data.replace("periodo_", "", 1)
    await query.message.reply_text(
        listar_horarios_periodo(periodo, "principal"),
        parse_mode="HTML",
        reply_markup=teclado_voltar_menu(),
    )


def criar_aplicacao() -> Application:
    validar_configuracao()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("onde", onde))
    application.add_handler(CommandHandler("local", local))
    application.add_handler(CommandHandler("rota", rota_atual))
    application.add_handler(CommandHandler("horarios", horarios))
    application.add_handler(CommandHandler("listar_horarios", comando_listar_horarios))

    application.add_handler(CallbackQueryHandler(botao_menu, pattern="^menu$"))
    application.add_handler(CallbackQueryHandler(botao_onde, pattern="^onde$"))
    application.add_handler(CallbackQueryHandler(botao_local, pattern="^local$"))
    application.add_handler(CallbackQueryHandler(botao_registrar_ponto, pattern="^local_"))
    application.add_handler(CallbackQueryHandler(botao_rota, pattern="^rota$"))
    application.add_handler(CallbackQueryHandler(botao_horarios, pattern="^horarios$"))
    application.add_handler(
        CallbackQueryHandler(botao_listar_horarios, pattern="^listar_horarios$")
    )
    application.add_handler(CallbackQueryHandler(botao_periodo, pattern="^periodo_"))

    return application


def main() -> None:
    application = criar_aplicacao()

    logger.info("BUSIVS BOT iniciado.")
    application.run_polling()


if __name__ == "__main__":
    main()
