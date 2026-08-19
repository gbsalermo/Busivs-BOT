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

# Depois de um RU suspeito, estes pontos constituem evidência forte de que o
# veículo realmente encerrou a volta anterior e já iniciou uma nova volta.
PONTOS_CLAROS_NOVA_VOLTA_POS_RU = {
    "fitotecnia",
    "solos_neas_florestal",
    "pavilhao_1",
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
    async def _carregar_indicacao_fraca(self):
        estado = await self._carregar()
        return estado.get("confirmacao_nao_confiavel")

    async def _salvar_indicacao_fraca(self, estado, ponto_id, ponto_anterior):
        estado["confirmacao_nao_confiavel"] = {
            "ponto_id": ponto_id,
            "ponto_anterior": ponto_anterior,
            "horario": agora_local().isoformat(),
        }
        await self._salvar(estado)

    async def _limpar_indicacao_fraca(self, estado=None):
        estado = estado or await self._carregar()
        estado.pop("confirmacao_nao_confiavel", None)
        await self._salvar(estado)
        return estado

    async def _resolver_indicacao_fraca_com_novo_ponto(self, ponto_id, telegram_id):
        """Resolve uma indicação suspeita sem deixá-la contaminar a rota confiável.

        A indicação fraca nunca substitui imediatamente o estado confiável. A
        próxima evidência decide o que aconteceu. Para RU suspeito, Fitotecnia,
        Solos ou Pav. I comprovam que uma nova volta já começou; Biblioteca
        contradiz o encerramento e mantém a volta anterior em andamento.
        """
        estado = await self._carregar()
        fraca = estado.get("confirmacao_nao_confiavel")
        if not fraca:
            return None

        ponto_fraco = fraca.get("ponto_id")

        # RU suspeito não pode encerrar a volta sozinho.
        if ponto_fraco == "ru":
            if ponto_id in PONTOS_CLAROS_NOVA_VOLTA_POS_RU:
                # A nova evidência prova operacionalmente que houve passagem pelo
                # RU entre as duas voltas. Limpamos a hipótese e registramos o
                # ponto novo diretamente como primeira evidência da nova volta.
                estado.pop("confirmacao_nao_confiavel", None)
                await self._salvar(estado)

                # Reiniciamos apenas a posição colaborativa para que a sequência
                # da volta anterior não impeça Fitotecnia/Solos/Pav. I.
                estado_novo = {
                    "ponto_anterior": None,
                    "ponto_atual": None,
                    "horario": None,
                    "telegram_id": None,
                    "resultado_rota": None,
                    "historico": list(estado.get("historico", []))[-40:],
                }
                # Preserva a referência; o wrapper superior ajusta para a próxima
                # referência quando a evidência de nova volta for processada.
                for chave in ("saida_referencia", "saida_referencia_manual"):
                    if chave in estado:
                        estado_novo[chave] = estado[chave]
                await self._salvar(estado_novo)
                return await super().registrar(ponto_id, telegram_id)

            if ponto_id == "biblioteca":
                # Biblioteca logo após P1 é coerente com o retorno da MESMA volta.
                # O RU suspeito é descartado e Biblioteca passa a ser o foco real.
                estado.pop("confirmacao_nao_confiavel", None)
                await self._salvar(estado)
                return await super().registrar(ponto_id, telegram_id)

            # Qualquer outra evidência normal também tem prioridade sobre a
            # hipótese fraca, mas não usamos o RU para encerrar a volta.
            estado.pop("confirmacao_nao_confiavel", None)
            await self._salvar(estado)
            return await super().registrar(ponto_id, telegram_id)

        # Para outras indicações fracas, a próxima evidência normal simplesmente
        # substitui a hipótese e é avaliada a partir do último estado confiável.
        estado.pop("confirmacao_nao_confiavel", None)
        await self._salvar(estado)
        return await super().registrar(ponto_id, telegram_id)

    async def registrar(self, ponto_id, telegram_id=None):
        # Se já existe uma indicação fraca, a nova evidência deve resolvê-la antes
        # de qualquer outra inferência ou mudança de volta.
        resolvido = await self._resolver_indicacao_fraca_com_novo_ponto(ponto_id, telegram_id)
        if resolvido is not None:
            return resolvido

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
        return resultado

    async def confirmar_ponto_suspeito(self, ponto_id, telegram_id=None):
        chave = f"ponto_suspeito:{telegram_id}"
        pendente = await self.ctx.storage.get(chave)
        if not pendente or pendente.get("ponto_novo") != ponto_id:
            return {"aceito": False, "motivo": "confirmacao_suspeita_expirada"}
        await self.ctx.storage.delete(chave)

        # Não registramos a indicação suspeita como posição oficial. Ela fica
        # paralela ao estado confiável até que outra evidência a confirme ou a
        # contradiga. Isso é essencial para RU não encerrar uma volta por engano.
        estado = await self._carregar()
        await self._salvar_indicacao_fraca(
            estado,
            ponto_id,
            pendente.get("ponto_anterior"),
        )
        return {
            "aceito": True,
            "nao_confiavel": True,
            "ponto_id": ponto_id,
            "ponto_anterior": pendente.get("ponto_anterior"),
        }

    async def cancelar_ponto_suspeito(self, telegram_id=None):
        await self.ctx.storage.delete(f"ponto_suspeito:{telegram_id}")
        return {"ok": True}

    async def localizacao(self):
        resposta = await super().localizacao()
        estado = await self._carregar()
        fraca = estado.get("confirmacao_nao_confiavel")
        if fraca:
            nome = PONTOS.get(fraca.get("ponto_id"), {}).get("nome", "ponto informado")
            resposta["texto"] += (
                f"\n\n⚠️ <b>Indicação não confirmada: {nome}.</b>"
                "\n📍 A última localização confiável continua sendo a referência."
                "\n🔎 Outra confirmação de ponto é necessária para validar o trajeto."
            )

        # RU confiável é chegada/fim da volta. Uma indicação fraca de RU nunca
        # chega aqui como ponto_atual, portanto não dispara fim de volta.
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
                    "📍 Indicação registrada como não confirmada.\n⚠️ Ela não altera o fim da volta nem a última localização confiável até surgir outra evidência.",
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
