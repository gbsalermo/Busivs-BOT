"""Configuração central do BUSIVS BOT.

Este módulo localiza o arquivo ``.env``, carrega as variáveis de ambiente e
expõe as configurações necessárias para iniciar o bot. A intenção é manter
segredos, como o token do Telegram, fora do código-fonte.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# A raiz do projeto fica um nível acima de ``src``. Usar Path evita depender
# do diretório em que o comando ``python src/bot.py`` foi executado.
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Carrega as variáveis definidas no .env para o ambiente do processo.
load_dotenv(ENV_PATH)

# O token é lido uma única vez quando este módulo é importado.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def validar_configuracao() -> None:
    """Garante que as configurações mínimas existem antes de iniciar o bot.

    Raises:
        RuntimeError: quando ``TELEGRAM_BOT_TOKEN`` não foi configurado.

    A validação acontece antes da criação da aplicação do Telegram para que o
    erro apareça de forma clara, em vez de falhar depois durante uma chamada de
    rede.
    """
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN nao configurado. "
            "Copie .env.example para .env e informe o token do bot."
        )
