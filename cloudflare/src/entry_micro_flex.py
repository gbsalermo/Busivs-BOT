from datetime import datetime, timedelta

import entry_ultima_volta as _entry
from entry_ultima_volta import *
from entry_core import enviar_mensagem, teclado_voltar, tempo_micro
from micro import faixa_funcional_micro, micro_pode_ser_ativado_agora, referencia_micro_proxima
from regras import agora_local


class BusState(_entry.BusState):
    async def _expirar_micro_se_necessario(self):
        if not await self.ctx.storage.get("micro_ativo"):
            return

        expira_em = await self.ctx.storage.get("micro_expira_em")
        if not expira_em:
            return

        try:
            limite = datetime.fromisoformat(str(expira_em))
        except Exception:
            await self.desativar_micro()
            return

        if agora_local() >= limite:
            await self.desativar_micro()

    async def micro_status(self):
        await self._expirar_micro_se_necessario()
        return {
            "ativo": bool(await self.ctx.storage.get("micro_ativo")),
            "ativado_em": await self.ctx.storage.get("micro_ativado_em"),
            "expira_em": await self.ctx.storage.get("micro_expira_em"),
            "modo": await self.ctx.storage.get("micro_modo"),
            "referencia_hora": await self.ctx.storage.get("micro_referencia_hora"),
            "referencia_origem": await self.ctx.storage.get("micro_referencia_origem"),
        }

    async def ativar_micro(self, admin_override=False):
        await self._expirar_micro_se_necessario()
        if await self.ctx.storage.get("micro_ativo"):
            return {"ok": True, "ja_ativo": True, **(await self.micro_status())}

        agora = agora_local()
        if not admin_override and not micro_pode_ser_ativado_agora(agora):
            return {"ok": False, "ja_ativo": False, "motivo": "fora_horario_micro"}

        referencia = referencia_micro_proxima(agora)
        faixa = faixa_funcional_micro(agora)

        if faixa and faixa["inicio"] <= agora < faixa["fim"]:
            expira = faixa["fim"]
        else:
            # Override administrativo fora da faixa funcional: evita sessão
            # esporádica esquecida indefinidamente.
            expira = agora + timedelta(minutes=30)

        await self.ctx.storage.put("micro_ativo", True)
        await self.ctx.storage.put("micro_ativado_em", agora.isoformat())
        await self.ctx.storage.put("micro_expira_em", expira.isoformat())
        await self.ctx.storage.delete("estado_micro")

        if referencia:
            await self.ctx.storage.put("micro_modo", "referenciado")
            await self.ctx.storage.put("micro_referencia_hora", referencia["hora"])
            await self.ctx.storage.put("micro_referencia_origem", referencia.get("origem", ""))
        else:
            await self.ctx.storage.put("micro_modo", "esporadico")
            await self.ctx.storage.delete("micro_referencia_hora")
            await self.ctx.storage.delete("micro_referencia_origem")

        return {"ok": True, "ja_ativo": False, **(await self.micro_status())}

    async def desativar_micro(self):
        resultado = await super().desativar_micro()
        await self.ctx.storage.delete("micro_modo")
        await self.ctx.storage.delete("micro_referencia_hora")
        await self.ctx.storage.delete("micro_referencia_origem")
        return resultado


class Default(_entry.Default):
    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao == "micro_confirmar_sim":
            resultado = await self._estado().ativar_micro(
                admin_override=self._telegram_admin(telegram_id)
            )
            if not resultado.get("ok"):
                return await enviar_mensagem(
                    self.env.TELEGRAM_BOT_TOKEN,
                    chat_id,
                    "🚫 O micro não pode ser ativado neste horário.\n\n"
                    "Para usuários, a confirmação fica disponível na faixa funcional do reforço, "
                    "inclusive quando ele estiver rodando fora de uma volta oficial específica.",
                    reply_markup=teclado_voltar(),
                )

            if resultado.get("ja_ativo"):
                return await self._menu(chat_id, telegram_id)

            texto = "🚐 Obrigado pela informação! O micro foi marcado como em operação."
            if resultado.get("modo") == "referenciado" and resultado.get("referencia_hora"):
                texto += (
                    "\n\n🧭 Referência associada: "
                    f"{resultado['referencia_hora']} — {resultado.get('referencia_origem', '')}."
                )
            else:
                texto += "\n\n🔵 Operação esporádica, sem vínculo obrigatório com uma volta oficial."

            tempo = tempo_micro(resultado)
            if tempo:
                texto += "\n" + tempo
            return await enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                texto,
                parse_mode="HTML",
                reply_markup=teclado_voltar(),
            )

        return await super()._acao(acao, chat_id, telegram_id)
