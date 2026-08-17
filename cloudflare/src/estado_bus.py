import estado_bus_core as _core

from transicao_bloco import confirmacao_inicia_novo_bloco
from volta_referencia import (
    aplicar_referencia,
    retornar_volta_anterior as _retornar_volta_anterior,
    resumo_referenciado,
    saida_ru_recente,
    ultima_saida_oficial,
    viagem_por_referencia,
)


class BusState(_core.BusState):
    async def registrar(self, ponto_id, telegram_id=None):
        estado_antes = await self._carregar()
        agora = _core.agora_local()
        referencia_antes = estado_antes.get("saida_referencia")
        referencia_manual_antes = bool(estado_antes.get("saida_referencia_manual"))
        sem_ponto_antes = not estado_antes.get("ponto_atual")
        transicao = confirmacao_inicia_novo_bloco(estado_antes, ponto_id, agora)

        resultado = await super().registrar(ponto_id, telegram_id)
        if not resultado.get("aceito"):
            return resultado

        estado = await self._carregar()

        if resultado.get("bloco_encerrado") or resultado.get("garagem_confirmada"):
            estado.pop("saida_referencia", None)
            estado.pop("saida_referencia_manual", None)
        elif ponto_id == "ru" and (transicao or sem_ponto_antes):
            viagem = saida_ru_recente(agora)
            if viagem:
                aplicar_referencia(estado, viagem, manual=False)
        elif transicao:
            viagem = ultima_saida_oficial(agora)
            if viagem:
                aplicar_referencia(estado, viagem, manual=False)
        elif referencia_antes:
            estado["saida_referencia"] = referencia_antes
            estado["saida_referencia_manual"] = referencia_manual_antes

        await self._salvar(estado)
        return resultado

    async def resumo_horarios(self):
        estado = await self._carregar()
        agora = _core.agora_local()
        estado = _core.reiniciar_se_novo_ciclo_noturno(estado, agora)
        estado = _core.expirar_confirmacao_volta_anterior(estado, agora)
        await self._salvar(estado)
        texto_padrao = _core.montar_resumo_horarios(estado=estado, agora=agora)
        return {"texto": resumo_referenciado(estado, agora, texto_padrao)}

    async def localizacao(self):
        resposta = await super().localizacao()
        estado = await self._carregar()
        viagem = viagem_por_referencia(estado)
        if viagem:
            modo = "ajustada manualmente" if estado.get("saida_referencia_manual") else "confirmada"
            resposta["texto"] += (
                "\n\n🧭 Referência da volta: "
                f"{viagem['hora']} — {viagem.get('origem', '')} ({modo})."
            )
        return resposta

    async def retornar_volta_anterior(self):
        estado = await self._carregar()
        agora = _core.agora_local()
        estado, anterior = _retornar_volta_anterior(estado, agora)
        if anterior is None:
            return {"ok": False, "motivo": "sem_volta_anterior"}
        await self._salvar(estado)
        return {
            "ok": True,
            "hora": anterior["hora"],
            "origem": anterior.get("origem", ""),
        }
