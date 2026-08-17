import estado_bus_core as _core

from dados import BLOCOS_PRINCIPAL, HORARIOS
from transicao_bloco import confirmacao_inicia_novo_bloco
from volta_referencia import (
    aplicar_referencia,
    limpar_referencia_expirada,
    proxima_volta_provavel,
    resumo_referenciado,
    saida_ru_recente,
    ultima_saida_oficial,
    viagem_por_referencia,
)


def _minutos(hora):
    h, m = map(int, hora.split(":"))
    return h * 60 + m


def _bloco_por_referencia(hora):
    if not hora:
        return None
    minuto = _minutos(hora)
    candidatos = []
    for bloco in BLOCOS_PRINCIPAL:
        inicio = _minutos(bloco["inicio"])
        fim = _minutos(bloco["ultima"])
        if inicio <= minuto <= fim:
            candidatos.append(bloco)
    return candidatos[0] if candidatos else None


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

        provavel = proxima_volta_provavel(estado, agora)
        texto_padrao = _core.montar_resumo_horarios(estado=estado, agora=agora)
        texto = resumo_referenciado(estado, agora, texto_padrao)
        if provavel is not None:
            estado = limpar_referencia_expirada(estado, agora)

        await self._salvar(estado)
        return {"texto": texto}

    async def localizacao(self):
        resposta = await super().localizacao()
        estado = await self._carregar()
        agora = _core.agora_local()
        viagem = viagem_por_referencia(estado)
        provavel = proxima_volta_provavel(estado, agora)

        if provavel:
            atual = provavel["viagem_anterior"]
            proxima = provavel["viagem_provavel"]
            resposta["texto"] += (
                "\n\n🟡 Próxima volta provavelmente em andamento."
                f"\n🕐 Referência provável: {proxima['hora']} — {proxima.get('origem', '')}."
                f"\n📌 Última volta confirmada: {atual['hora']} — {atual.get('origem', '')}."
                "\nℹ️ Essa transição é estimada; uma nova confirmação tem prioridade."
            )
            estado = limpar_referencia_expirada(estado, agora)
            await self._salvar(estado)
        elif viagem:
            modo = "ajustada manualmente" if estado.get("saida_referencia_manual") else "confirmada"
            resposta["texto"] += (
                "\n\n🧭 Referência da volta: "
                f"{viagem['hora']} — {viagem.get('origem', '')} ({modo})."
            )
        return resposta

    async def definir_volta_referencia(self, hora):
        viagem = next((v for v in HORARIOS.get("principal", []) if v.get("hora") == hora), None)
        if viagem is None:
            return {"ok": False, "motivo": "horario_invalido"}

        estado = await self._carregar()
        aplicar_referencia(estado, viagem, manual=True)
        await self._salvar(estado)
        return {
            "ok": True,
            "hora": viagem["hora"],
            "origem": viagem.get("origem", ""),
        }

    async def encerrar_bloco_admin(self):
        estado = await self._carregar()
        agora = _core.agora_local()
        referencia = estado.get("saida_referencia")

        if referencia:
            bloco = _bloco_por_referencia(referencia)
        else:
            minuto = agora.hour * 60 + agora.minute
            candidatos = [
                bloco for bloco in BLOCOS_PRINCIPAL
                if _minutos(bloco["inicio"]) <= minuto
            ]
            bloco = max(candidatos, key=lambda b: _minutos(b["inicio"])) if candidatos else None

        if bloco is None:
            return {"ok": False, "motivo": "sem_bloco"}

        historico = list(estado.get("historico", []))
        historico.append({
            "ponto_id": "garagem",
            "horario": agora.isoformat(),
            "telegram_id": "admin",
        })

        estado.update({
            "ponto_anterior": estado.get("ponto_atual"),
            "ponto_atual": "garagem",
            "horario": agora.isoformat(),
            "resultado_rota": {
                "operacao_encerrada_bloco": True,
                "garagem_confirmada": True,
                "bloco_id": bloco["id"],
                "inicio_bloco": bloco["inicio"],
                "ultima_volta": bloco["ultima"],
                "fim_previsto": agora.isoformat(),
            },
            "historico": historico[-40:],
        })
        estado.pop("saida_referencia", None)
        estado.pop("saida_referencia_manual", None)
        await self._salvar(estado)

        return {
            "ok": True,
            "bloco_id": bloco["id"],
            "inicio": bloco["inicio"],
            "ultima": bloco["ultima"],
        }
