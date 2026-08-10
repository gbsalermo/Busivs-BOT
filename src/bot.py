import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, validar_configuracao
from horarios import listar_horarios_periodo, montar_resumo_horarios
from rota import analisar_trecho, formatar_situacao_rota

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# Temporário: usado apenas para validar a experiência do botão "Onde está o ônibus?"
# antes de implementarmos o registro real de passagens.
PONTO_ANTERIOR_SIMULADO = "portao_1"
PONTO_ATUAL_SIMULADO = "biblioteca"


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
        ]
    )


def montar_localizacao_simulada() -> str:
    resultado = analisar_trecho(
        PONTO_ANTERIOR_SIMULADO,
        PONTO_ATUAL_SIMULADO,
    )

    situacao = formatar_situacao_rota(resultado)

    return (
        "🧪 MODO SIMULAÇÃO\n\n"
        f"{situacao}\n\n"
        "ℹ️ Esta localização é apenas para teste da Etapa 3. "
        "Ainda não representa uma confirmação real de passagem."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🚌 Onde está o ônibus?", callback_data="onde")],
        [InlineKeyboardButton("📍 Informar passagem", callback_data="local")],
        [InlineKeyboardButton("⏰ Próximos horários", callback_data="horarios")],
        [InlineKeyboardButton("📋 Listar horários", callback_data="listar_horarios")],
        [InlineKeyboardButton("🗺️ Rota atual", callback_data="rota")],
        [InlineKeyboardButton("📢 Avisos", callback_data="avisos")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    mensagem = update.effective_message

    if mensagem is None:
        return

    await mensagem.reply_text(
        "🚌 BUSIVS BOT\n\n"
        "Acompanhe o circular da UFRB de forma colaborativa.\n\n"
        "Escolha uma opção:",
        reply_markup=reply_markup,
    )


async def onde(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensagem = update.effective_message
    if mensagem:
        await mensagem.reply_text(montar_localizacao_simulada())


async def botao_onde(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(montar_localizacao_simulada())


async def horarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensagem = update.effective_message
    if mensagem:
        await mensagem.reply_text(
            montar_resumo_horarios("principal"),
            parse_mode="HTML",
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
    )


def criar_aplicacao() -> Application:
    validar_configuracao()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("onde", onde))
    application.add_handler(CommandHandler("horarios", horarios))
    application.add_handler(CommandHandler("listar_horarios", comando_listar_horarios))
    application.add_handler(CallbackQueryHandler(botao_onde, pattern="^onde$"))
    application.add_handler(CallbackQueryHandler(botao_horarios, pattern="^horarios$"))
    application.add_handler(
        CallbackQueryHandler(botao_listar_horarios, pattern="^listar_horarios$")
    )
    application.add_handler(
        CallbackQueryHandler(botao_periodo, pattern="^periodo_")
    )

    return application


def main() -> None:
    application = criar_aplicacao()

    logger.info("BUSIVS BOT iniciado.")
    application.run_polling()


if __name__ == "__main__":
    main()
