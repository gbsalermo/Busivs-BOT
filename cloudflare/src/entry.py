from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

from telegram_api import (
    configurar_webhook,
    enviar_mensagem,
    remover_webhook,
    responder_callback,
)


HEADER_SEGREDO_TELEGRAM = "X-Telegram-Bot-Api-Secret-Token"
HEADER_ADMIN = "X-BUSIVS-Admin-Secret"


def _teclado_menu_principal() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "🚌 Onde está o ônibus?", "callback_data": "onde"}],
            [{"text": "📍 Informar passagem", "callback_data": "local"}],
            [{"text": "⏰ Próximos horários", "callback_data": "horarios"}],
            [{"text": "📋 Listar horários", "callback_data": "listar_horarios"}],
            [{"text": "🗺️ Rota atual", "callback_data": "rota"}],
            [{"text": "📢 Avisos", "callback_data": "avisos"}],
        ]
    }


def _teclado_voltar() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}]
        ]
    }


def _extrair_mensagem(update: dict) -> dict | None:
    return update.get("message") or update.get("edited_message")


def _extrair_callback(update: dict) -> dict | None:
    return update.get("callback_query")


def _chat_id_da_mensagem(mensagem: dict | None) -> int | None:
    if not mensagem:
        return None
    return (mensagem.get("chat") or {}).get("id")


def _chat_id_do_callback(callback: dict | None) -> int | None:
    if not callback:
        return None
    mensagem = callback.get("message") or {}
    return (mensagem.get("chat") or {}).get("id")


class Default(WorkerEntrypoint):
    async def _enviar_menu(self, chat_id: int) -> dict:
        return await enviar_mensagem(
            self.env.TELEGRAM_BOT_TOKEN,
            chat_id,
            "🚌 BUSIVS BOT\n\n"
            "Acompanhe o circular da UFRB de forma colaborativa.\n\n"
            "Escolha uma opção:",
            reply_markup=_teclado_menu_principal(),
        )

    def _admin_autorizado(self, request) -> bool:
        recebido = request.headers.get(HEADER_ADMIN)
        esperado = self.env.TELEGRAM_WEBHOOK_SECRET
        return bool(recebido and recebido == esperado)

    async def fetch(self, request):
        parsed = urlparse(request.url)
        caminho = parsed.path
        method = request.method

        if method == "GET" and caminho == "/health":
            return Response.json(
                {
                    "status": "ok",
                    "service": "busivs-bot",
                    "runtime": "cloudflare-worker",
                    "stage": "6.3-validation",
                }
            )

        if method == "POST" and caminho == "/admin/telegram/set-webhook":
            if not self._admin_autorizado(request):
                return Response.json({"ok": False, "error": "admin_secret_invalid"}, status=403)

            origem = f"{parsed.scheme}://{parsed.netloc}"
            webhook_url = f"{origem}/telegram/webhook"
            resultado = await configurar_webhook(
                self.env.TELEGRAM_BOT_TOKEN,
                webhook_url,
                self.env.TELEGRAM_WEBHOOK_SECRET,
            )
            return Response.json(
                {
                    "ok": resultado["ok_http"],
                    "webhook_url": webhook_url,
                    "telegram": resultado["telegram"],
                },
                status=200 if resultado["ok_http"] else 502,
            )

        if method == "POST" and caminho == "/admin/telegram/delete-webhook":
            if not self._admin_autorizado(request):
                return Response.json({"ok": False, "error": "admin_secret_invalid"}, status=403)

            resultado = await remover_webhook(self.env.TELEGRAM_BOT_TOKEN)
            return Response.json(
                {
                    "ok": resultado["ok_http"],
                    "telegram": resultado["telegram"],
                },
                status=200 if resultado["ok_http"] else 502,
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
                return Response.json({"ok": False, "error": "invalid_json"}, status=400)

            mensagem = _extrair_mensagem(update)
            callback = _extrair_callback(update)

            if mensagem:
                chat_id = _chat_id_da_mensagem(mensagem)
                if chat_id is None:
                    return Response.json({"ok": True, "handled": False})

                texto = (mensagem.get("text") or "").strip()
                if texto == "/start":
                    envio = await self._enviar_menu(chat_id)
                else:
                    envio = await enviar_mensagem(
                        self.env.TELEGRAM_BOT_TOKEN,
                        chat_id,
                        "Use /start para abrir o menu do BUSIVS.",
                        reply_markup=_teclado_voltar(),
                    )

                return Response.json(
                    {
                        "ok": envio["ok_http"],
                        "handled": True,
                        "stage": "6.3-validation",
                    },
                    status=200 if envio["ok_http"] else 502,
                )

            if callback:
                callback_id = callback.get("id")
                if callback_id:
                    await responder_callback(self.env.TELEGRAM_BOT_TOKEN, callback_id)

                chat_id = _chat_id_do_callback(callback)
                if chat_id is None:
                    return Response.json({"ok": True, "handled": False})

                acao = callback.get("data") or ""

                if acao == "menu":
                    envio = await self._enviar_menu(chat_id)
                else:
                    nomes = {
                        "onde": "🚌 Onde está o ônibus?",
                        "local": "📍 Informar passagem",
                        "horarios": "⏰ Próximos horários",
                        "listar_horarios": "📋 Listar horários",
                        "rota": "🗺️ Rota atual",
                        "avisos": "📢 Avisos",
                    }
                    titulo = nomes.get(acao, "BUSIVS")
                    envio = await enviar_mensagem(
                        self.env.TELEGRAM_BOT_TOKEN,
                        chat_id,
                        f"{titulo}\n\n☁️ Botão recebido pelo Worker com sucesso.\nA regra de negócio será conectada nesta sequência de migração.",
                        reply_markup=_teclado_voltar(),
                    )

                return Response.json(
                    {
                        "ok": envio["ok_http"],
                        "handled": True,
                        "callback": acao,
                        "stage": "6.3-validation",
                    },
                    status=200 if envio["ok_http"] else 502,
                )

            return Response.json(
                {
                    "ok": True,
                    "handled": False,
                    "reason": "update_type_not_supported_yet",
                    "stage": "6.3-validation",
                }
            )

        return Response.json(
            {
                "service": "BUSIVS BOT",
                "status": "cloudflare-adapter-running",
                "stage": "6.3-validation",
                "health": "/health",
                "webhook": "/telegram/webhook",
            }
        )
