from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

from telegram_api import enviar_mensagem


HEADER_SEGREDO_TELEGRAM = "X-Telegram-Bot-Api-Secret-Token"


def _extrair_chat_id(update: dict) -> int | None:
    mensagem = update.get("message") or update.get("edited_message")
    if not mensagem:
        return None

    chat = mensagem.get("chat") or {}
    return chat.get("id")


def _extrair_texto(update: dict) -> str | None:
    mensagem = update.get("message") or update.get("edited_message")
    if not mensagem:
        return None

    return mensagem.get("text")


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        caminho = urlparse(request.url).path
        method = request.method

        if method == "GET" and caminho == "/health":
            return Response.json(
                {
                    "status": "ok",
                    "service": "busivs-bot",
                    "runtime": "cloudflare-worker",
                    "stage": "6.2",
                }
            )

        if method == "POST" and caminho == "/telegram/webhook":
            segredo_recebido = request.headers.get(HEADER_SEGREDO_TELEGRAM)
            segredo_esperado = self.env.TELEGRAM_WEBHOOK_SECRET

            if not segredo_recebido or segredo_recebido != segredo_esperado:
                return Response.json(
                    {"ok": False, "error": "webhook_secret_invalid"},
                    status=403,
                )

            try:
                update = await request.json()
            except Exception:
                return Response.json(
                    {"ok": False, "error": "invalid_json"},
                    status=400,
                )

            chat_id = _extrair_chat_id(update)
            texto = _extrair_texto(update)

            # Nesta subetapa callbacks e outros tipos de Update são apenas
            # reconhecidos e ignorados com sucesso. Eles serão tratados na 6.3.
            if chat_id is None:
                return Response.json(
                    {
                        "ok": True,
                        "handled": False,
                        "reason": "update_type_not_supported_yet",
                        "stage": "6.2",
                    }
                )

            resposta_texto = (
                "☁️ BUSIVS Cloudflare ativo.\n\n"
                "O webhook recebeu sua mensagem com sucesso."
            )

            if texto == "/start":
                resposta_texto = (
                    "☁️ BUSIVS Cloudflare ativo.\n\n"
                    "Webhook validado com sucesso. A interface completa será conectada na próxima etapa."
                )

            envio = await enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                resposta_texto,
            )

            if not envio["ok_http"]:
                return Response.json(
                    {
                        "ok": False,
                        "error": "telegram_send_failed",
                        "telegram_status": envio["status"],
                    },
                    status=502,
                )

            return Response.json(
                {
                    "ok": True,
                    "handled": True,
                    "stage": "6.2",
                }
            )

        return Response.json(
            {
                "service": "BUSIVS BOT",
                "status": "cloudflare-adapter-running",
                "stage": "6.2",
                "health": "/health",
                "webhook": "/telegram/webhook",
            }
        )
