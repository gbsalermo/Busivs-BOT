import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, validar_configuracao
from horarios import montar_resumo_horarios

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🚌 Onde está o ônibus?", callback_data="onde")],
        [InlineKeyboardButton("📍 Informar passagem", callback_data="local")],
        [InlineKeyboardButton("⏰ Próximos horários", callback_data="horarios")],
        [InlineKeyboardButton("🗺️ Rota atual", callback_data="rota")],
        [InlineKeyboardButton("📢 Avisos", callback_data="avisos")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🚌 BUSIVS BOT\n\n"
        "Acompanhe o circular da UFRB de forma colaborativa.\n\n"
        "Escolha uma opção:",
        reply_markup=reply_markup,
    )


async def horarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(montar_resumo_horarios("principal"))


async def botao_horarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(montar_resumo_horarios("principal"))


def criar_aplicacao() -> Application:
    validar_configuracao()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("horarios", horarios))
    application.add_handler(CallbackQueryHandler(botao_horarios, pattern="^horarios$"))

    return application


def main() -> None:
    application = criar_aplicacao()

    logger.info("BUSIVS BOT iniciado.")
    application.run_polling()


if __name__ == "__main__":
    main()
