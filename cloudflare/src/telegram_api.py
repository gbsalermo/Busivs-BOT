import json

from js import Object, fetch
from pyodide.ffi import to_js as _to_js


def _to_js_object(valor):
    return _to_js(valor, dict_converter=Object.fromEntries)


async def enviar_mensagem(token: str, chat_id: int, texto: str) -> dict:
    """Envia uma mensagem simples usando diretamente a Telegram Bot API.

    Nesta versão Cloudflare evitamos depender de python-telegram-bot dentro do
    Worker. A camada de transporte fica pequena e explícita; a regra de negócio
    será portada separadamente nas próximas subetapas.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
    }

    opcoes = _to_js_object(
        {
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload),
        }
    )

    resposta = await fetch(url, opcoes)
    dados = await resposta.json()

    return {
        "ok_http": bool(resposta.ok),
        "status": int(resposta.status),
        "telegram": dados.to_py() if hasattr(dados, "to_py") else dados,
    }
