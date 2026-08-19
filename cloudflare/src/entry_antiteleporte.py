from datetime import datetime

import entry_admin_hub as _entry
from entry_admin_hub import *
import entry_core as _core
from dados import PONTOS
from regras import agora_local


# Apenas saltos muito característicos recebem uma checagem temporal. Eles nunca
# são bloqueados: viram uma indicação não confiável até a próxima evidência.
LIMITES_SUSPEITOS = {
    ("fitotecnia", "biblioteca"): 60,
    ("biblioteca", "portao_1"): 120,
    ("portao_1", "biblioteca"): 60,
    ("portao_1", "ru"): 120,
}


def _dt(valor):
    try:
        return datetime.fromisoformat(str(valor)) if valor else None
    except Exception:
        return None


def _suspeita(estado, ponto, agora):
    anterior = (estado or {}).get("ponto_atual")
    limite = LIMITES_SUSPEITOS.get((anterior, ponto))
    if not limite:
        return None
    horario = _dt((estado or {}).get("horario"))
    if not horario or horario.date() != agora.date() or agora < horario:
        return None
    decorrido = int((agora - horario).total_seconds())
    if decorrido >= limite:
        return None
    return {"ponto_anterior": anterior, "ponto_novo": ponto, "segundos": decorrido, "limite": limite}


def _teclado_confirmar(ponto):
    return {"inline_keyboard": [
        [{"text": "✅ Sim, tenho certeza", "callback_data": f"confirmar_ponto_{ponto}"}],
        [{"text": "❌ Marquei errado", "callback_data": "cancelar_ponto_suspeito"}],
    ]}


class BusState(_entry.BusState):
    async def registrar(self, ponto_id, telegram_id=None):
        estado = await self._carregar()
        agora = agora_local()
        suspeita = _suspeita(estado, ponto_id, agora)
        if suspeita:
            await self.ctx.storage.put(f"ponto_suspeito:{telegram_id}", {
                **suspeita,
                "telegram_id": str(telegram_id),
                "criado_em": agora.isoformat(),
            })
            return {"aceito": False, "motivo": "confirmacao_suspeita", **suspeita}

        resultado = await super().registrar(ponto_id, telegram_id)
        if resultado.get("aceito"):
            estado = await self._carregar()
            # Qualquer nova evidência normal substitui uma indicação fraca anterior.
            estado.pop("confirmacao_nao_confiavel", None)
            await self._salvar(estado)
        return resultado

    async def confirmar_ponto_suspeito(self, ponto_id, telegram_id=None):
        chave = f"ponto_suspeito:{telegram_id}"
        pendente = await self.ctx.storage.get(chave)
        if not pendente or pendente.get("ponto_novo") != ponto_id:
            return {"aceito": False, "motivo": "confirmacao_suspeita_expirada"}
        await self.ctx.storage.delete(chave)
        resultado = await super().registrar(ponto_id, telegram_id)
        if resultado.get("aceito"):
            estado = await self._carregar()
            estado["confirmacao_nao_confiavel"] = {
                "ponto_id": ponto_id,
                "ponto_anterior": pendente.get("ponto_anterior"),
                "horario": agora_local().isoformat(),
            }
            await self._salvar(estado)
            resultado["nao_confiavel"] = True
        return resultado

    async def cancelar_ponto_suspeito(self, telegram_id=None):
        await self.ctx.storage.delete(f"ponto_suspeito:{telegram_id}")
        return {"ok": True}

    async def localizacao(self):
        resposta = await super().localizacao()
        estado = await self._carregar()
        fraca = estado.get("confirmacao_nao_confiavel")
        if fraca:
            resposta["texto"] += (
                "\n\n⚠️ <b>Última indicação ainda não é confiável.</b>"
                "\n📍 Outra confirmação de ponto é necessária para confirmar a localização."
            )
        # RU é chegada/fim da volta. A saída seguinte não é criada pelo relógio:
        # Fitotecnia é só o primeiro ponto esperado; qualquer ponto de ida pode
        # comprovar depois que a nova volta começou.
        if estado.get("ponto_atual") == "ru":
            resposta["texto"] = resposta["texto"].replace("➡️ Sentido: RUA", "🏁 Chegada ao RU — fim da volta.")
            if "Fitotecnia" not in resposta["texto"] and "Garagem" not in resposta["texto"]:
                resposta["texto"] += "\n\n🔄 Se houver nova volta, o primeiro ponto esperado é Fitotecnia."
        return resposta


class Default(_entry.Default):
    async def _resultado_ponto(self, chat_id, resultado):
        if resultado.get("motivo") == "confirmacao_suspeita":
            ponto = resultado.get("ponto_novo")
            nome = PONTOS.get(ponto, {}).get("nome", "esse ponto")
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                f"⚠️ Essa marcação em <b>{nome}</b> aconteceu muito rápido em relação à última localização.\n\nVocê tem certeza de que viu o circular nesse ponto?",
                parse_mode="HTML",
                reply_markup=_teclado_confirmar(ponto),
            )
        return await super()._resultado_ponto(chat_id, resultado)

    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao.startswith("confirmar_ponto_"):
            ponto = acao.replace("confirmar_ponto_", "", 1)
            resultado = await self._estado().confirmar_ponto_suspeito(ponto, telegram_id)
            if resultado.get("aceito"):
                return await _core.enviar_mensagem(
                    self.env.TELEGRAM_BOT_TOKEN,
                    chat_id,
                    "📍 Indicação registrada.\n⚠️ Como o deslocamento foi muito rápido, outra confirmação de ponto ainda é necessária para validar a localização.",
                    reply_markup=_core.teclado_voltar(),
                )
            return await self._resultado_ponto(chat_id, resultado)
        if acao == "cancelar_ponto_suspeito":
            await self._estado().cancelar_ponto_suspeito(telegram_id)
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "Tudo certo. A marcação anterior foi mantida.",
                reply_markup=_core.teclado_voltar(),
            )
        return await super()._acao(acao, chat_id, telegram_id)
