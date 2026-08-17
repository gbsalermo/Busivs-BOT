import entry_engajamento_teste as _teste
from entry_engajamento_teste import *


_teclado_localizacao_original = _teste._entry.teclado_localizacao


def teclado_localizacao_com_teste(admin=False):
    teclado = _teclado_localizacao_original(admin)
    if not admin:
        return teclado

    linhas = list(teclado.get("inline_keyboard", []))
    botao = [{"text": "🧪 Testar aviso agora", "callback_data": "admin_teste_engajamento"}]
    indice_voltar = max(0, len(linhas) - 1)
    linhas.insert(indice_voltar, botao)
    return {"inline_keyboard": linhas}


# O handler herdado de entry.py resolve essa função no módulo entry.
# O patch afeta apenas o entrypoint temporário de teste do main.
_teste._entry.teclado_localizacao = teclado_localizacao_com_teste


class Default(_teste.Default):
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
