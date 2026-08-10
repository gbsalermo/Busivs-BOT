"""Interface Telegram do BUSIVS BOT.

Este é o ponto de entrada da aplicação. O arquivo cria os teclados, recebe
comandos/callbacks do Telegram e delega as regras de negócio para os módulos
``horarios.py``, ``passagens.py`` e ``rota.py``.

Regra de organização:
- este módulo cuida da conversa e da apresentação;
- ``horarios.py`` calcula horários e estimativas;
- ``passagens.py`` mantém o estado colaborativo do ônibus;
- ``rota.py`` interpreta a sequência física dos pontos.

Assim, os handlers do Telegram permanecem simples e não duplicam regras de
negócio.
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, validar_configuracao
from horarios import listar_horarios_periodo, montar_resumo_horarios
from passagens import montar_localizacao_atual, registrar_passagem
from rota import carregar_pontos, carregar_rota

# Configuração básica de log para acompanhar inicialização e futuros erros do
# processo sem depender de prints espalhados pelo código.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# Rótulos mais curtos para os botões do Telegram. Os nomes completos continuam
# guardados em data/pontos.json; aqui só definimos como eles aparecem na UI.
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
    """Monta o teclado principal exibido ao abrir ou retornar ao menu."""
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
    """Retorna o botão padrão usado para voltar ao menu principal."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")]]
    )


def teclado_periodos() -> InlineKeyboardMarkup:
    """Cria os botões de seleção dos períodos usados em 'Listar horários'."""
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
    """Cria dinamicamente o teclado de confirmação de passagem.

    Os pontos vêm do JSON, portanto adicionar um ponto ao cadastro não exige
    escrever manualmente um novo botão aqui. Os botões são organizados em duas
    colunas para não ocupar espaço excessivo no Telegram.
    """
    pontos = carregar_pontos()
    botoes = []

    for ponto_id in pontos:
        rotulo = ROTULOS_PONTOS.get(ponto_id, pontos[ponto_id]["nome"])
        botoes.append(
            InlineKeyboardButton(rotulo, callback_data=f"local_{ponto_id}")
        )

    # Divide a lista de botões em grupos de dois por linha.
    linhas = [botoes[i : i + 2] for i in range(0, len(botoes), 2)]
    linhas.append([InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu")])
    return InlineKeyboardMarkup(linhas)


def montar_rota_atual() -> str:
    """Monta a rota completa em texto para exibição no Telegram.

    A função apenas apresenta os dados de ``rotas.json`` e ``pontos.json``.
    Pontos opcionais recebem uma marcação visual e a mudança para o trecho de
    volta é destacada após o último ponto externo.
    """
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

        # Após Canãa, a sequência já está entrando novamente no campus.
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
    """Envia a mensagem inicial e o teclado principal para uma conversa."""
    await mensagem.reply_text(
        "🚌 BUSIVS BOT\n\n"
        "Acompanhe o circular da UFRB de forma colaborativa.\n\n"
        "Escolha uma opção:",
        reply_markup=teclado_menu_principal(),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler do comando ``/start``."""
    mensagem = update.effective_message
    if mensagem is None:
        return

    await enviar_menu(mensagem)


async def botao_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback do botão 'Voltar ao menu'."""
    query = update.callback_query
    await query.answer()
    await enviar_menu(query.message)


async def onde(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler do comando ``/onde`` para consultar a localização atual."""
    mensagem = update.effective_message
    if mensagem:
        await mensagem.reply_text(
            montar_localizacao_atual(),
            reply_markup=teclado_voltar_menu(),
        )


async def botao_onde(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Versão por botão da consulta 'Onde está o ônibus?'."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        montar_localizacao_atual(),
        reply_markup=teclado_voltar_menu(),
    )


async def local(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler do comando ``/local`` que abre o teclado de pontos."""
    mensagem = update.effective_message
    if mensagem:
        await mensagem.reply_text(
            "📍 Onde o ônibus acabou de passar?\n\n"
            "Toque no ponto correspondente.",
            reply_markup=teclado_pontos(),
        )


async def botao_local(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Versão por botão do fluxo de informar passagem."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📍 Onde o ônibus acabou de passar?\n\n"
        "Toque no ponto correspondente.",
        reply_markup=teclado_pontos(),
    )


async def botao_registrar_ponto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recebe o ponto selecionado e tenta registrá-lo como passagem real.

    O ``callback_data`` tem o formato ``local_<id>``. O ID do usuário é enviado
    para ``passagens.py`` apenas como contexto interno do registro; a resposta
    ao usuário depende do motivo retornado pela regra de negócio.
    """
    query = update.callback_query
    await query.answer()

    ponto_id = query.data.replace("local_", "", 1)
    usuario = update.effective_user
    telegram_id = usuario.id if usuario else None

    resultado = registrar_passagem(ponto_id, telegram_id)

    if not resultado["aceito"]:
        # Uma repetição do mesmo ponto não precisa expor regras internas. Para
        # o aluno, basta agradecer a tentativa de colaborar.
        if resultado["motivo"] == "duplicado":
            await query.message.reply_text(
                "Obrigado pela informação 😊",
                reply_markup=teclado_voltar_menu(),
            )
            return

        # Fora de circulação, o bot rejeita a confirmação e usa o horário
        # oficial apenas para explicar onde o ônibus provavelmente está.
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
    """Handler do comando ``/rota``."""
    mensagem = update.effective_message
    if mensagem:
        await mensagem.reply_text(
            montar_rota_atual(),
            reply_markup=teclado_voltar_menu(),
        )


async def botao_rota(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback do botão 'Rota atual'."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        montar_rota_atual(),
        reply_markup=teclado_voltar_menu(),
    )


async def horarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler do comando ``/horarios`` para o resumo dos próximos horários."""
    mensagem = update.effective_message
    if mensagem:
        await mensagem.reply_text(
            montar_resumo_horarios("principal"),
            parse_mode="HTML",
            reply_markup=teclado_voltar_menu(),
        )


async def comando_listar_horarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler que abre a escolha de período para listar horários completos."""
    mensagem = update.effective_message
    if mensagem:
        await mensagem.reply_text(
            "📋 Qual período você quer consultar?",
            reply_markup=teclado_periodos(),
        )


async def botao_horarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback do botão 'Próximos horários'."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        montar_resumo_horarios("principal"),
        parse_mode="HTML",
        reply_markup=teclado_voltar_menu(),
    )


async def botao_listar_horarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback do botão 'Listar horários'."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📋 Qual período você quer consultar?",
        reply_markup=teclado_periodos(),
    )


async def botao_periodo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista os horários do período escolhido no teclado.

    O callback chega como ``periodo_manha``, ``periodo_tarde`` etc. O prefixo é
    removido antes de chamar a função de horários.
    """
    query = update.callback_query
    await query.answer()

    periodo = query.data.replace("periodo_", "", 1)
    await query.message.reply_text(
        listar_horarios_periodo(periodo, "principal"),
        parse_mode="HTML",
        reply_markup=teclado_voltar_menu(),
    )


def criar_aplicacao() -> Application:
    """Cria a aplicação Telegram e registra todos os handlers disponíveis.

    A configuração é validada antes da conexão. ``CommandHandler`` responde a
    comandos digitados; ``CallbackQueryHandler`` responde aos botões inline.
    Os ``pattern`` impedem que um callback seja tratado pelo handler errado.
    """
    validar_configuracao()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Comandos que também podem ser digitados diretamente no Telegram.
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("onde", onde))
    application.add_handler(CommandHandler("local", local))
    application.add_handler(CommandHandler("rota", rota_atual))
    application.add_handler(CommandHandler("horarios", horarios))
    application.add_handler(CommandHandler("listar_horarios", comando_listar_horarios))

    # Ações disparadas pelos botões da interface.
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
    """Inicializa o bot e mantém o processo ouvindo o Telegram por polling."""
    application = criar_aplicacao()

    logger.info("BUSIVS BOT iniciado.")
    application.run_polling()


# Permite executar este arquivo diretamente com ``python src/bot.py`` sem
# disparar ``main`` quando o módulo for importado em testes ou outras rotinas.
if __name__ == "__main__":
    main()
