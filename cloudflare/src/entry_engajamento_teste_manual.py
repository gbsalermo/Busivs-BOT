import entry_engajamento_teste as _teste
from entry_engajamento_teste import *


def teclado_teste_manual():
    return {"inline_keyboard": [
        [{"text": "🧪 Testar aviso agora", "callback_data": "admin_teste_engajamento"}],
    ]}


class Default(_teste.Default):
    async def _onde(self, chat_id, telegram_id=None):
        envio = await super()._onde(chat_id, telegram_id)
        if self._telegram_admin(telegram_id):
            await _teste._entry._core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "🧪 DIAGNÓSTICO TEMPORÁRIO\n\n"
                "Se esta mensagem apareceu, o Worker já está rodando a versão nova. "
                "Use o botão abaixo para testar um envio ativo para o seu próprio chat.",
                reply_markup=teclado_teste_manual(),
            )
        return envio

    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao == "admin_teste_engajamento":
            if not self._telegram_admin(telegram_id):
                return {"ok_http": True, "status": 200, "telegram": {"ok": True}}

            admin_id = str(self.env.ADMIN_TELEGRAM_ID).strip()
            return await _teste._entry._core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                admin_id,
                "🧪 TESTE MANUAL DE COLABORAÇÃO\n\n"
                "🚌 Você viu o circular recentemente?\n\n"
                "Este envio foi forçado manualmente fora do horário para validar "
                "se o BUSIVS consegue iniciar uma mensagem para o seu chat.",
                reply_markup=_teste.teclado_convite(),
            )

        return await super()._acao(acao, chat_id, telegram_id)

    async def scheduled(self, controller, env, ctx):
        admin_id = str(self.env.ADMIN_TELEGRAM_ID).strip()
        candidato = await self._estado().candidato_engajamento_teste(admin_id)
        if not candidato.get("enviar"):
            return
        await _teste._entry._core.enviar_mensagem(
            self.env.TELEGRAM_BOT_TOKEN,
            admin_id,
            "🧪 TESTE DE COLABORAÇÃO\n\n"
            "🚌 Você viu o circular recentemente?\n\n"
            "A localização continua sem nova confirmação. "
            "Se você viu o ônibus passar, ajude atualizando o ponto.",
            reply_markup=_teste.teclado_convite(),
        )
