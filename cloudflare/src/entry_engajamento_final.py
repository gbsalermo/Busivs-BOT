"""Camada final de produção com engajamento colaborativo ativo.

Mantém `entry_consistencia` como base funcional e reaproveita a regra já
consolidada de `entry_engajamento` sem recolocar heurísticas antigas na cadeia
de localização. Esta camada existe para garantir que consultas em "Onde está o
ônibus?" alimentem os candidatos e que o cron execute os pedidos de confirmação.
"""

import entry_consistencia as _entry
from entry_consistencia import *
import entry_engajamento as _eng
import entry_core as _core
import entry_admin as _admin

# Em produção, cada lote pode alcançar até 20 usuários que consultaram a
# localização durante a lacuna atual. A seleção e os demais filtros continuam
# sendo executados pela regra consolidada de entry_engajamento.
_eng.MAX_CONVIDADOS = 20


class BusState(_entry.BusState):
    # Reaproveita somente as rotinas de estado de engajamento. As regras de
    # posição, referência, antiteleporte e fim de bloco continuam vindo da
    # cadeia final de entry_consistencia -> entry_antiteleporte.
    registrar_consulta_engajamento = _eng.BusState.registrar_consulta_engajamento
    registrar_convite_engajamento = _eng.BusState.registrar_convite_engajamento
    consumir_convite_engajamento = _eng.BusState.consumir_convite_engajamento
    _consultas_da_janela = _eng.BusState._consultas_da_janela
    candidatos_engajamento = _eng.BusState.candidatos_engajamento


class Default(_entry.Default):
    async def _onde(self, chat_id, telegram_id=None):
        # Somente usuários comuns entram como candidatos. A consulta é
        # registrada antes da resposta para simular a dinâmica do grupo: quem
        # procurou a localização recentemente pode ser perguntado depois.
        if telegram_id is not None and not self._telegram_admin(telegram_id):
            await self._estado().registrar_consulta_engajamento(telegram_id)
        return await super()._onde(chat_id, telegram_id)

    async def _convite_expirado(self, chat_id, telegram_id=None):
        return await _core.enviar_mensagem(
            self.env.TELEGRAM_BOT_TOKEN,
            chat_id,
            "⌛ Este pedido de confirmação expirou.\n\n"
            "Os botões desse aviso ficam disponíveis por 3 minutos. "
            "Se você estiver vendo o circular agora, use 📍 Marcar ponto pelo menu.",
            reply_markup=_admin.teclado_localizacao_admin(self._telegram_admin(telegram_id)),
        )

    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao.startswith("engajamento_local_"):
            token = acao.replace("engajamento_local_", "", 1)
            convite = await self._estado().consumir_convite_engajamento(telegram_id, token)
            if not convite.get("ok"):
                return await self._convite_expirado(chat_id, telegram_id)
            return await super()._acao("local", chat_id, telegram_id)

        if acao.startswith("engajamento_nao_vi_"):
            token = acao.replace("engajamento_nao_vi_", "", 1)
            convite = await self._estado().consumir_convite_engajamento(telegram_id, token)
            if not convite.get("ok"):
                return await self._convite_expirado(chat_id, telegram_id)
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "👍 Tudo bem. Obrigado por responder!",
                reply_markup=_admin.teclado_localizacao_admin(self._telegram_admin(telegram_id)),
            )

        return await super()._acao(acao, chat_id, telegram_id)

    async def scheduled(self, controller, env, ctx):
        candidatos = await self._estado().candidatos_engajamento()
        if not candidatos.get("enviar"):
            return

        texto = (
            "🚌 Você viu o circular recentemente?\n\n"
            "A localização está há alguns minutos sem nova confirmação. "
            "Se você viu o ônibus passar, ajude atualizando o ponto.\n\n"
            "⏳ Este pedido pode ser respondido por até 3 minutos."
        )

        for telegram_id in candidatos.get("ids", []):
            token = await self._estado().registrar_convite_engajamento(telegram_id)
            await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                telegram_id,
                texto,
                reply_markup=_eng.teclado_convite(token),
            )
