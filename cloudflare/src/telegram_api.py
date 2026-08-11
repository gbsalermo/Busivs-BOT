import json
from js import Object, fetch
from pyodide.ffi import to_js as _to_js


def _js(valor):
    return _to_js(valor, dict_converter=Object.fromEntries)


async def _post_telegram(token: str, metodo: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{metodo}"
    resposta = await fetch(
        url,
        _js({
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload, ensure_ascii=False),
        }),
    )
    texto = await resposta.text()
    try:
        dados = json.loads(texto)
    except Exception:
        dados = {"raw": texto}
    return {"ok_http": bool(resposta.ok), "status": int(resposta.status), "telegram": dados}


async def enviar_mensagem(token, chat_id, texto, reply_markup=None, parse_mode=None):
    payload = {"chat_id": chat_id, "text": texto}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    if parse_mode is not None:
        payload["parse_mode"] = parse_mode
    return await _post_telegram(token, "sendMessage", payload)


async def responder_callback(token, callback_query_id):
    return await _post_telegram(token, "answerCallbackQuery", {"callback_query_id": callback_query_id})


async def configurar_webhook(token, webhook_url, secret_token):
    return await _post_telegram(token, "setWebhook", {
        "url": webhook_url,
        "secret_token": secret_token,
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": True,
    })


async def remover_webhook(token):
    return await _post_telegram(token, "deleteWebhook", {"drop_pending_updates": True})
