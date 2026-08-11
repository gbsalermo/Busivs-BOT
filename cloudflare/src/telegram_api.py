import json

from js import Object, fetch
from pyodide.ffi import to_js as _to_js


def _to_js_object(valor):
    return _to_js(valor, dict_converter=Object.fromEntries)


async def _post_telegram(token: str, metodo: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{metodo}"
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


async def enviar_mensagem(
    token: str,
    chat_id: int,
    texto: str,
    reply_markup: dict | None = None,
    parse_mode: str | None = None,
) -> dict:
    payload = {
        "chat_id": chat_id,
        "text": texto,
    }

    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    if parse_mode is not None:
        payload["parse_mode"] = parse_mode

    return await _post_telegram(token, "sendMessage", payload)


async def responder_callback(token: str, callback_query_id: str) -> dict:
    return await _post_telegram(
        token,
        "answerCallbackQuery",
        {"callback_query_id": callback_query_id},
    )


async def configurar_webhook(
    token: str,
    webhook_url: str,
    secret_token: str,
) -> dict:
    return await _post_telegram(
        token,
        "setWebhook",
        {
            "url": webhook_url,
            "secret_token": secret_token,
            "allowed_updates": ["message", "callback_query"],
            "drop_pending_updates": True,
        },
    )


async def remover_webhook(token: str) -> dict:
    return await _post_telegram(
        token,
        "deleteWebhook",
        {"drop_pending_updates": True},
    )
