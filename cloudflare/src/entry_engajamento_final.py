"""Camada final de produção com engajamento colaborativo e analytics isolado.

Mantém `entry_consistencia` como base funcional e reaproveita a regra já
consolidada de `entry_engajamento` sem recolocar heurísticas antigas na cadeia
de localização. Analytics é gravado em paralelo e nunca participa das decisões
de rota, referência, bloco, antiteleporte ou confiabilidade.
"""

import analytics as _analytics
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

    def _analytics_admin(self, telegram_id):
        try:
            esperado = str(self.env.ADMIN_TELEGRAM_ID).strip()
        except Exception:
            return False
        return bool(esperado and str(telegram_id) == esperado)

    async def registrar_evento_analytics(self, telegram_id, evento, admin=False, contar_interacao=True):
        return await _analytics.registrar_evento(
            self.ctx.storage,
            telegram_id,
            evento,
            admin=admin,
            contar_interacao=contar_interacao,
        )

    async def resumo_analytics(self, dias=1):
        return await _analytics.resumo(self.ctx.storage, dias)

    async def registrar(self, ponto_id, telegram_id=None):
        resultado = await super().registrar(ponto_id, telegram_id)
        if resultado.get("aceito") and telegram_id is not None:
            try:
                await self.registrar_evento_analytics(
                    telegram_id,
                    "confirmacao_principal",
                    admin=self._analytics_admin(telegram_id),
                    contar_interacao=False,
                )
            except Exception:
                pass
        return resultado

    async def registrar_micro(self, ponto_id, telegram_id=None):
        resultado = await super().registrar_micro(ponto_id, telegram_id)
        if resultado.get("aceito") and telegram_id is not None:
            try:
                await self.registrar_evento_analytics(
                    telegram_id,
                    "confirmacao_micro",
                    admin=self._analytics_admin(telegram_id),
                    contar_interacao=False,
                )
            except Exception:
                pass
        return resultado


class Default(_entry.Default):
    async def _analytics_seguro(self, telegram_id, evento, contar_interacao=True):
        """Analytics nunca pode impedir uma resposta normal do bot."""
        if telegram_id is None:
            return
        try:
            await self._estado().registrar_evento_analytics(
                telegram_id,
                evento,
                self._telegram_admin(telegram_id),
                contar_interacao,
            )
        except Exception:
            pass

    def _evento_acao(self, acao):
        if acao == "onde":
            return "consulta_localizacao"
        if acao == "local":
            return "abrir_marcacao"
        if acao == "horarios":
            return "proximos_horarios"
        if acao == "listar_horarios" or acao.startswith("periodo_"):
            return "listar_horarios"
        if acao.startswith("local_principal_"):
            return "marcacao_principal"
        if acao.startswith("local_micro_"):
            return "marcacao_micro"
        if acao in {"micro_confirmar", "micro_confirmar_sim", "micro_ativo", "veiculo_micro"}:
            return "micro"
        if acao in {"ajuda", "manual", "rota", "feedback"}:
            return acao
        if acao == "menu":
            return "menu"
        if acao == "desconhecido":
            return "comando_desconhecido"
        if acao.startswith("admin_") or acao.startswith("aviso_") or acao == "avisos":
            return "admin"
        return "outra_acao"

    async def _menu(self, chat_id, telegram_id=None, boas_vindas=False):
        if boas_vindas:
            await self._analytics_seguro(telegram_id, "inicio")
        return await super()._menu(chat_id, telegram_id, boas_vindas)

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
                await self._analytics_seguro(telegram_id, "engajamento_expirado")
                return await self._convite_expirado(chat_id, telegram_id)
            await self._analytics_seguro(telegram_id, "engajamento_sim")
            return await super()._acao("local", chat_id, telegram_id)

        if acao.startswith("engajamento_nao_vi_"):
            token = acao.replace("engajamento_nao_vi_", "", 1)
            convite = await self._estado().consumir_convite_engajamento(telegram_id, token)
            if not convite.get("ok"):
                await self._analytics_seguro(telegram_id, "engajamento_expirado")
                return await self._convite_expirado(chat_id, telegram_id)
            await self._analytics_seguro(telegram_id, "engajamento_nao_vi")
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "👍 Tudo bem. Obrigado por responder!",
                reply_markup=_admin.teclado_localizacao_admin(self._telegram_admin(telegram_id)),
            )

        await self._analytics_seguro(telegram_id, self._evento_acao(acao))
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
            envio = await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                telegram_id,
                texto,
                reply_markup=_eng.teclado_convite(token),
            )
            if envio.get("ok_http"):
                await self._analytics_seguro(telegram_id, "engajamento_enviado", contar_interacao=False)
