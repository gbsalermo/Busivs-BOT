from datetime import datetime

import entry_admin_hub as _entry
from entry_admin_hub import *
import entry_core as _core
from dados import BLOCOS_PRINCIPAL, HORARIOS, PONTOS
from regras import agora_local
from registro_colaborativo import (
    evidencia_nova_volta,
    registrar_sem_relogio,
    reiniciar_posicao_para_nova_volta,
    texto_localizacao_colaborativa,
)
from volta_referencia import aplicar_referencia, proxima_apos_referencia


# Apenas saltos muito característicos recebem uma checagem temporal. Eles nunca
# são bloqueados: viram uma indicação não confiável até a próxima evidência.
# As mesmas regras valem para Principal e Micro.
LIMITES_SUSPEITOS = {
    ("fitotecnia", "biblioteca"): 60,
    ("biblioteca", "portao_1"): 120,
    ("portao_1", "biblioteca"): 60,
    ("portao_1", "ru"): 120,
}

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
    return {
        "ponto_anterior": anterior,
        "ponto_novo": ponto,
        "segundos": decorrido,
        "limite": limite,
    }


def _teclado_confirmar(ponto, micro=False):
    if micro:
        confirmar = f"confirmar_micro_ponto_{ponto}"
        cancelar = "cancelar_micro_ponto_suspeito"
    else:
        confirmar = f"confirmar_ponto_{ponto}"
        cancelar = "cancelar_ponto_suspeito"
    return {
        "inline_keyboard": [
            [{"text": "✅ Sim, tenho certeza", "callback_data": confirmar}],
            [{"text": "❌ Marquei errado", "callback_data": cancelar}],
        ]
    }


def _bloco_referencia_principal(hora):
    if not hora:
        return None
    minuto = int(hora[:2]) * 60 + int(hora[3:5])
    for bloco in BLOCOS_PRINCIPAL:
        ini = int(bloco["inicio"][:2]) * 60 + int(bloco["inicio"][3:5])
        fim = int(bloco["ultima"][:2]) * 60 + int(bloco["ultima"][3:5])
        if ini <= minuto <= fim:
            return bloco
    return None


def _proxima_referencia_mesmo_bloco(estado):
    atual = (estado or {}).get("saida_referencia")
    proxima = proxima_apos_referencia(estado)
    if not atual or not proxima:
        return None
    bloco = _bloco_referencia_principal(atual)
    if not bloco:
        return proxima
    minuto = int(proxima["hora"][:2]) * 60 + int(proxima["hora"][3:5])
    ini = int(bloco["inicio"][:2]) * 60 + int(bloco["inicio"][3:5])
    fim = int(bloco["ultima"][:2]) * 60 + int(bloco["ultima"][3:5])
    return proxima if ini <= minuto <= fim else None


def _proxima_referencia_micro(hora_atual):
    horarios = HORARIOS.get("micro", [])
    if not hora_atual:
        return None
    indice = next((i for i, item in enumerate(horarios) if item.get("hora") == hora_atual), None)
    if indice is None or indice + 1 >= len(horarios):
        return None
    atual = horarios[indice]
    proxima = horarios[indice + 1]
    ha = int(atual["hora"][:2]) * 60 + int(atual["hora"][3:5])
    hp = int(proxima["hora"][:2]) * 60 + int(proxima["hora"][3:5])
    # Não pula automaticamente de um bloco do micro para outro distante.
    return proxima if hp - ha <= 90 else None


class BusState(_entry.BusState):
    async def _salvar_indicacao_fraca(self, estado, ponto_id, ponto_anterior, micro=False):
        estado["confirmacao_nao_confiavel"] = {
            "ponto_id": ponto_id,
            "ponto_anterior": ponto_anterior,
            "horario": agora_local().isoformat(),
        }
        if micro:
            await self._salvar_chave_estado("estado_micro", estado)
        else:
            await self._salvar(estado)

    async def _registrar_principal_confiavel(self, ponto_id, telegram_id=None):
        estado = await self._carregar()
        if evidencia_nova_volta(estado, ponto_id):
            proxima = _proxima_referencia_mesmo_bloco(estado)
            # Se a referência atual já é a última do bloco, Fitotecnia/Solos
            # podem ser retorno à Garagem; não inventamos uma nova volta.
            if not estado.get("saida_referencia") or proxima is not None:
                novo = reiniciar_posicao_para_nova_volta(estado)
                if proxima is not None:
                    aplicar_referencia(novo, proxima, manual=False)
                await self._salvar(novo)
        return await super().registrar(ponto_id, telegram_id)

    async def _avancar_referencia_micro_se_houver(self):
        atual = await self.ctx.storage.get("micro_referencia_hora")
        proxima = _proxima_referencia_micro(atual)
        if proxima:
            await self.ctx.storage.put("micro_modo", "referenciado")
            await self.ctx.storage.put("micro_referencia_hora", proxima["hora"])
            await self.ctx.storage.put("micro_referencia_origem", proxima.get("origem", ""))
            return proxima
        # Se o micro seguir rodando além da última referência do bloco, passa a
        # ser tratado como esporádico em vez de saltar para outro bloco pelo relógio.
        if atual:
            await self.ctx.storage.put("micro_modo", "esporadico")
            await self.ctx.storage.delete("micro_referencia_hora")
            await self.ctx.storage.delete("micro_referencia_origem")
        return None

    async def _registrar_micro_confiavel(self, ponto_id, telegram_id=None):
        await self._expirar_micro_se_necessario()
        if not await self.ctx.storage.get("micro_ativo"):
            return {"aceito": False, "motivo": "micro_inativo"}

        estado = await self._carregar_chave_estado("estado_micro")
        agora = agora_local()
        if evidencia_nova_volta(estado, ponto_id):
            estado = reiniciar_posicao_para_nova_volta(estado)
            await self._avancar_referencia_micro_se_houver()

        estado, resultado = registrar_sem_relogio(estado, ponto_id, telegram_id, agora)
        await self._salvar_chave_estado("estado_micro", estado)
        return resultado

    async def _resolver_indicacao_fraca_principal(self, ponto_id, telegram_id):
        estado = await self._carregar()
        fraca = estado.get("confirmacao_nao_confiavel")
        if not fraca:
            return None

        ponto_fraco = fraca.get("ponto_id")
        estado.pop("confirmacao_nao_confiavel", None)
        await self._salvar(estado)

        if ponto_fraco == "ru" and ponto_id in PONTOS_CLAROS_NOVA_VOLTA_POS_RU:
            return await self._registrar_principal_confiavel(ponto_id, telegram_id)

        # Biblioteca após P1 contradiz um RU suspeito; qualquer nova evidência
        # normal também vence a hipótese fraca e parte do último estado confiável.
        return await self._registrar_principal_confiavel(ponto_id, telegram_id)

    async def _resolver_indicacao_fraca_micro(self, ponto_id, telegram_id):
        estado = await self._carregar_chave_estado("estado_micro")
        fraca = estado.get("confirmacao_nao_confiavel")
        if not fraca:
            return None

        estado.pop("confirmacao_nao_confiavel", None)
        await self._salvar_chave_estado("estado_micro", estado)
        return await self._registrar_micro_confiavel(ponto_id, telegram_id)

    async def registrar(self, ponto_id, telegram_id=None):
        resolvido = await self._resolver_indicacao_fraca_principal(ponto_id, telegram_id)
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
            return {"aceito": False, "motivo": "confirmacao_suspeita", "veiculo": "principal", **suspeita}

        return await self._registrar_principal_confiavel(ponto_id, telegram_id)

    async def registrar_micro(self, ponto_id, telegram_id=None):
        resolvido = await self._resolver_indicacao_fraca_micro(ponto_id, telegram_id)
        if resolvido is not None:
            return resolvido

        await self._expirar_micro_se_necessario()
        if not await self.ctx.storage.get("micro_ativo"):
            return {"aceito": False, "motivo": "micro_inativo"}

        estado = await self._carregar_chave_estado("estado_micro")
        agora = agora_local()
        suspeita = _suspeita(estado, ponto_id, agora)
        if suspeita:
            await self.ctx.storage.put(f"micro_ponto_suspeito:{telegram_id}", {
                **suspeita,
                "telegram_id": str(telegram_id),
                "criado_em": agora.isoformat(),
            })
            return {"aceito": False, "motivo": "confirmacao_suspeita", "veiculo": "micro", **suspeita}

        return await self._registrar_micro_confiavel(ponto_id, telegram_id)

    async def confirmar_ponto_suspeito(self, ponto_id, telegram_id=None, micro=False):
        prefixo = "micro_ponto_suspeito" if micro else "ponto_suspeito"
        chave = f"{prefixo}:{telegram_id}"
        pendente = await self.ctx.storage.get(chave)
        if not pendente or pendente.get("ponto_novo") != ponto_id:
            return {"aceito": False, "motivo": "confirmacao_suspeita_expirada", "veiculo": "micro" if micro else "principal"}
        await self.ctx.storage.delete(chave)

        if micro:
            estado = await self._carregar_chave_estado("estado_micro")
        else:
            estado = await self._carregar()
        await self._salvar_indicacao_fraca(
            estado,
            ponto_id,
            pendente.get("ponto_anterior"),
            micro=micro,
        )
        return {
            "aceito": True,
            "nao_confiavel": True,
            "veiculo": "micro" if micro else "principal",
            "ponto_id": ponto_id,
            "ponto_anterior": pendente.get("ponto_anterior"),
        }

    async def cancelar_ponto_suspeito(self, telegram_id=None, micro=False):
        prefixo = "micro_ponto_suspeito" if micro else "ponto_suspeito"
        await self.ctx.storage.delete(f"{prefixo}:{telegram_id}")
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

        if estado.get("ponto_atual") == "ru":
            resposta["texto"] = resposta["texto"].replace("➡️ Sentido: RUA", "🏁 Chegada ao RU — fim da volta.")
            if "Fitotecnia" not in resposta["texto"] and "Garagem" not in resposta["texto"]:
                resposta["texto"] += "\n\n🔄 Se houver nova volta, o primeiro ponto esperado é Fitotecnia."
        return resposta

    async def localizacao_micro(self):
        await self._expirar_micro_se_necessario()
        estado = await self._carregar_chave_estado("estado_micro")
        if not await self.ctx.storage.get("micro_ativo"):
            return {"ativo": False, "estado": estado, "texto": ""}

        texto = texto_localizacao_colaborativa(estado, agora_local(), titulo="🚐 Micro")
        fraca = estado.get("confirmacao_nao_confiavel")
        if fraca:
            nome = PONTOS.get(fraca.get("ponto_id"), {}).get("nome", "ponto informado")
            texto += (
                f"\n\n⚠️ <b>Indicação não confirmada: {nome}.</b>"
                "\n📍 A última localização confiável continua sendo a referência."
                "\n🔎 Outra confirmação é necessária para validar o trajeto."
            )

        modo = await self.ctx.storage.get("micro_modo")
        ref = await self.ctx.storage.get("micro_referencia_hora")
        origem = await self.ctx.storage.get("micro_referencia_origem")
        if modo == "referenciado" and ref:
            texto += f"\n\n🧭 Referência da volta: {ref} — {origem or 'RU/Residências'}."
        elif modo == "esporadico":
            texto += "\n\n🔵 Operação esporádica, sem vínculo obrigatório com horário oficial."

        return {"ativo": True, "estado": estado, "texto": texto}


class Default(_entry.Default):
    async def _resultado_ponto(self, chat_id, resultado):
        if resultado.get("motivo") == "confirmacao_suspeita":
            ponto = resultado.get("ponto_novo")
            micro = resultado.get("veiculo") == "micro"
            nome = PONTOS.get(ponto, {}).get("nome", "esse ponto")
            veiculo = "micro" if micro else "circular"
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                f"⚠️ Essa marcação em <b>{nome}</b> aconteceu muito rápido em relação à última localização.\n\nVocê tem certeza de que viu o {veiculo} nesse ponto?",
                parse_mode="HTML",
                reply_markup=_teclado_confirmar(ponto, micro=micro),
            )
        return await super()._resultado_ponto(chat_id, resultado)

    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao.startswith("confirmar_micro_ponto_"):
            ponto = acao.replace("confirmar_micro_ponto_", "", 1)
            resultado = await self._estado().confirmar_ponto_suspeito(ponto, telegram_id, micro=True)
            if resultado.get("aceito"):
                return await _core.enviar_mensagem(
                    self.env.TELEGRAM_BOT_TOKEN,
                    chat_id,
                    "🚐 Indicação do micro registrada como não confirmada.\n⚠️ Ela não altera a última localização confiável nem encerra/inicia volta até surgir outra evidência.",
                    reply_markup=_core.teclado_voltar(),
                )
            return await self._resultado_ponto(chat_id, resultado)

        if acao == "cancelar_micro_ponto_suspeito":
            await self._estado().cancelar_ponto_suspeito(telegram_id, micro=True)
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "Tudo certo. A localização confiável anterior do micro foi mantida.",
                reply_markup=_core.teclado_voltar(),
            )

        if acao.startswith("confirmar_ponto_"):
            ponto = acao.replace("confirmar_ponto_", "", 1)
            resultado = await self._estado().confirmar_ponto_suspeito(ponto, telegram_id, micro=False)
            if resultado.get("aceito"):
                return await _core.enviar_mensagem(
                    self.env.TELEGRAM_BOT_TOKEN,
                    chat_id,
                    "📍 Indicação registrada como não confirmada.\n⚠️ Ela não altera o fim da volta nem a última localização confiável até surgir outra evidência.",
                    reply_markup=_core.teclado_voltar(),
                )
            return await self._resultado_ponto(chat_id, resultado)

        if acao == "cancelar_ponto_suspeito":
            await self._estado().cancelar_ponto_suspeito(telegram_id, micro=False)
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "Tudo certo. A marcação anterior foi mantida.",
                reply_markup=_core.teclado_voltar(),
            )
        return await super()._acao(acao, chat_id, telegram_id)
