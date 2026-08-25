import estado_bus_core as _core
from datetime import datetime, timedelta

from dados import BLOCOS_PRINCIPAL, HORARIOS, PONTOS, ROTA
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

MICRO_BIBLIOTECA_RETORNO_MINUTOS = 15


def _minutos(hora):
    h, m = map(int, hora.split(":"))
    return h * 60 + m


def _dt(valor):
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return None


def _indice_ponto_sentido(ponto_id, sentido):
    for indice, item in enumerate(ROTA):
        if item["ponto_id"] == ponto_id and item.get("sentido_apos") == sentido:
            return indice
    return None


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


def _proxima_referencia_programada_mesmo_bloco(estado):
    """Retorna a próxima volta da grade sem usar o relógio como gatilho.

    A chegada ao RU encerra a volta atual e pode preparar a referência seguinte
    do MESMO bloco, mesmo que o horário oficial dela ainda esteja alguns minutos
    à frente. Nunca atravessa automaticamente para outro bloco.
    """
    referencia = (estado or {}).get("saida_referencia")
    if not referencia:
        return None

    horarios = HORARIOS.get("principal", [])
    indice = next((i for i, viagem in enumerate(horarios) if viagem.get("hora") == referencia), None)
    if indice is None or indice + 1 >= len(horarios):
        return None

    atual = horarios[indice]
    proxima = horarios[indice + 1]
    bloco_atual = _bloco_por_referencia(atual.get("hora"))
    bloco_proximo = _bloco_por_referencia(proxima.get("hora"))
    if not bloco_atual or not bloco_proximo or bloco_atual.get("id") != bloco_proximo.get("id"):
        return None
    return proxima


def _bloco_atual_ou_referenciado(estado, agora):
    bloco = _bloco_por_referencia((estado or {}).get("saida_referencia"))
    if bloco is not None:
        return bloco

    minuto = agora.hour * 60 + agora.minute
    candidatos = [
        bloco for bloco in BLOCOS_PRINCIPAL
        if _minutos(bloco["inicio"]) <= minuto
    ]
    return max(candidatos, key=lambda b: _minutos(b["inicio"])) if candidatos else None


def _contexto_pos_ru(estado, agora):
    """Mostra o contexto pós-RU sem avançar referência pela passagem do tempo."""
    resultado = (estado or {}).get("resultado_rota") or {}
    if (estado or {}).get("ponto_atual") != "ru":
        return ""
    if resultado.get("ponto_atual_id") != "ru" or resultado.get("proximo") is not None:
        return ""

    referencia = viagem_por_referencia(estado)
    bloco = _bloco_atual_ou_referenciado(estado, agora)
    if bloco is None:
        return ""

    # Depois que o RU fecha uma volta, registrar() já deixa preparada a próxima
    # referência do mesmo bloco. A consulta apenas exibe esse estado; nunca usa
    # hora > agora para pular de 07:10 para 07:25, por exemplo.
    if referencia and referencia.get("hora") != bloco.get("ultima"):
        return (
            "\n\n⏰ Próxima saída prevista neste bloco:"
            f"\n     🕐 {referencia['hora']} — {referencia.get('origem', 'RU/Residências')}"
        )

    if referencia and referencia.get("hora") == bloco.get("ultima"):
        # Se a própria última referência acabou de ser preparada, ela ainda é a
        # próxima saída válida; se foi a volta fechada, não há outra no bloco.
        fechamento_ref = resultado.get("referencia_fechada")
        if fechamento_ref and fechamento_ref != referencia.get("hora"):
            return (
                "\n\n⏰ Próxima saída prevista neste bloco:"
                f"\n     🕐 {referencia['hora']} — {referencia.get('origem', 'RU/Residências')}"
            )

    return "\n\n🅿️ Sem nova saída neste bloco; o circular provavelmente segue para a Garagem."


def _enxugar_fim_volta_ru(texto):
    antigo = (
        "🏁 Chegada ao RU / fim da volta confirmada.\n"
        "🚌 O ônibus pode estar concluindo a volta anterior ou aguardando/iniciando uma nova saída.\n"
        "ℹ️ Não é possível afirmar o sentido apenas por esta confirmação; os horários podem sofrer atraso."
    )
    return texto.replace(antigo, "🏁 Fim da volta confirmado no RU.")


def _proximo_manual(indice):
    if indice + 1 >= len(ROTA):
        return None
    item = ROTA[indice + 1]
    ponto = PONTOS[item["ponto_id"]]
    proximo = {
        "id": ponto["id"],
        "nome": ponto["nome"],
        "opcional": item.get("opcional", ponto.get("opcional", False)),
    }
    if proximo["opcional"]:
        for proximo_indice in range(indice + 2, len(ROTA)):
            alternativa = ROTA[proximo_indice]
            if alternativa.get("opcional", False):
                continue
            ponto_alternativo = PONTOS[alternativa["ponto_id"]]
            proximo["alternativa"] = {
                "id": ponto_alternativo["id"],
                "nome": ponto_alternativo["nome"],
            }
            break
    return proximo


def _resultado_correcao_manual(ponto_id, sentido):
    if ponto_id not in PONTOS:
        return None

    if sentido == "GARAGEM":
        if ponto_id == "fitotecnia":
            proximo = {
                "id": "solos_neas_florestal",
                "nome": PONTOS["solos_neas_florestal"]["nome"],
                "opcional": False,
            }
        elif ponto_id == "solos_neas_florestal":
            proximo = {"id": "garagem", "nome": "Garagem", "opcional": False}
        else:
            return None
        return {
            "retorno_garagem": True,
            "correcao_admin": True,
            "ponto_atual_id": ponto_id,
            "ponto_atual": PONTOS[ponto_id]["nome"],
            "sentido": "GARAGEM",
            "proximo": proximo,
        }

    for indice, item in enumerate(ROTA):
        if item["ponto_id"] == ponto_id and item.get("sentido_apos") == sentido:
            return {
                "correcao_admin": True,
                "ponto_atual_id": ponto_id,
                "ponto_atual": PONTOS[ponto_id]["nome"],
                "indice_atual": indice,
                "sentido": sentido,
                "proximo": _proximo_manual(indice),
            }
    return None


def _deve_biblioteca_micro_ser_retorno(estado_antes, agora):
    if not estado_antes or not estado_antes.get("ponto_atual"):
        return False

    confirmado_em = _dt(estado_antes.get("horario"))
    if confirmado_em is None or confirmado_em.date() != agora.date():
        return False

    if agora - confirmado_em < timedelta(minutes=MICRO_BIBLIOTECA_RETORNO_MINUTOS):
        return False

    resultado = estado_antes.get("resultado_rota") or {}
    indice_atual = resultado.get("indice_atual")
    indice_biblioteca_ida = _indice_ponto_sentido("biblioteca", "RUA")
    indice_biblioteca_retorno = _indice_ponto_sentido("biblioteca", "RU")

    if indice_biblioteca_ida is None or indice_biblioteca_retorno is None:
        return False

    return indice_atual is not None and indice_atual < indice_biblioteca_ida


class BusState(_core.BusState):
    async def registrar_micro(self, ponto_id, telegram_id=None):
        estado_antes = await self._carregar_chave_estado("estado_micro")
        agora = _core.agora_local()
        forcar_biblioteca_retorno = (
            ponto_id == "biblioteca"
            and _deve_biblioteca_micro_ser_retorno(estado_antes, agora)
        )

        resultado = await super().registrar_micro(ponto_id, telegram_id)
        if not resultado.get("aceito") or not forcar_biblioteca_retorno:
            return resultado

        estado = await self._carregar_chave_estado("estado_micro")
        indice = _indice_ponto_sentido("biblioteca", "RU")
        if indice is None:
            return resultado

        resultado_rota = {
            "ponto_anterior": PONTOS.get(estado_antes.get("ponto_atual"), {}).get("nome"),
            "ponto_atual": PONTOS["biblioteca"]["nome"],
            "ponto_atual_id": "biblioteca",
            "indice_atual": indice,
            "sentido": "RU",
            "proximo": _proximo_manual(indice),
            "estimado_por_tempo": True,
            "tempo_minimo_retorno_min": MICRO_BIBLIOTECA_RETORNO_MINUTOS,
        }
        estado["resultado_rota"] = resultado_rota
        await self._salvar_chave_estado("estado_micro", estado)
        resultado["resultado_rota"] = resultado_rota
        resultado["biblioteca_retorno_por_tempo"] = True
        return resultado

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
        elif ponto_id == "ru" and resultado.get("fim_volta") and referencia_antes:
            # RU encerra a referência que estava rodando. Preparamos exatamente a
            # próxima volta do MESMO bloco; o relógio não pode pular outras depois.
            estado.setdefault("resultado_rota", {})["referencia_fechada"] = referencia_antes
            proxima = _proxima_referencia_programada_mesmo_bloco({"saida_referencia": referencia_antes})
            if proxima:
                aplicar_referencia(estado, proxima, manual=False)
            else:
                estado["saida_referencia"] = referencia_antes
                estado["saida_referencia_manual"] = referencia_manual_antes
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

        resposta["texto"] = _enxugar_fim_volta_ru(resposta["texto"])
        resposta["texto"] += _contexto_pos_ru(estado, agora)

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

    async def corrigir_ponto_sentido_admin(self, ponto_id, sentido):
        sentido = str(sentido or "").upper()
        resultado_rota = _resultado_correcao_manual(ponto_id, sentido)
        if resultado_rota is None:
            return {"ok": False, "motivo": "combinacao_invalida"}

        estado = await self._carregar()
        agora = _core.agora_local()
        anterior = estado.get("ponto_atual")
        historico = list(estado.get("historico", []))
        historico.append({
            "ponto_id": ponto_id,
            "horario": agora.isoformat(),
            "telegram_id": "admin",
            "correcao_manual": True,
            "sentido": sentido,
        })

        estado.update({
            "ponto_anterior": anterior,
            "ponto_atual": ponto_id,
            "horario": agora.isoformat(),
            "telegram_id": "admin",
            "resultado_rota": resultado_rota,
            "historico": historico[-40:],
        })
        await self._salvar(estado)

        return {
            "ok": True,
            "ponto_id": ponto_id,
            "ponto": PONTOS[ponto_id]["nome"],
            "sentido": sentido,
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