from datetime import timedelta

import entry_engajamento as _entry
from entry_engajamento import *
from dados import BLOCOS_PRINCIPAL, HORARIOS
from volta_referencia import ultima_saida_oficial, viagem_por_referencia


MARCADOR_FIM_BLOCO = "operacao_encerrada_bloco"
PONTOS_FINAIS_GARAGEM = {"ru", "fitotecnia", "solos_neas_florestal", "garagem"}


def _minutos(hora):
    h, m = map(int, hora.split(":"))
    return h * 60 + m


def _bloco_da_viagem(hora):
    if not hora:
        return None, None
    minuto = _minutos(hora)
    for indice, bloco in enumerate(BLOCOS_PRINCIPAL):
        if _minutos(bloco["inicio"]) <= minuto <= _minutos(bloco["ultima"]):
            return indice, bloco
    return None, None


def _viagem_por_hora(hora):
    return next((v for v in HORARIOS.get("principal", []) if v.get("hora") == hora), None)


def _proxima_saida_apos_bloco(indice_bloco, agora):
    if indice_bloco is None:
        return None

    if indice_bloco + 1 < len(BLOCOS_PRINCIPAL):
        proximo_bloco = BLOCOS_PRINCIPAL[indice_bloco + 1]
        viagem = _viagem_por_hora(proximo_bloco["inicio"])
        return {
            "viagem": viagem,
            "quando": agora.replace(
                hour=int(proximo_bloco["inicio"][:2]),
                minute=int(proximo_bloco["inicio"][3:5]),
                second=0,
                microsecond=0,
            ),
            "proximo_dia_util": False,
        }

    dias = 1
    proximo_dia = agora + timedelta(days=dias)
    while proximo_dia.weekday() >= 5:
        dias += 1
        proximo_dia = agora + timedelta(days=dias)

    primeiro = BLOCOS_PRINCIPAL[0]
    viagem = _viagem_por_hora(primeiro["inicio"])
    return {
        "viagem": viagem,
        "quando": proximo_dia.replace(
            hour=int(primeiro["inicio"][:2]),
            minute=int(primeiro["inicio"][3:5]),
            second=0,
            microsecond=0,
        ),
        "proximo_dia_util": True,
    }


def _formatar_proxima(proxima):
    if not proxima or not proxima.get("viagem"):
        return None
    viagem = proxima["viagem"]
    quando = proxima["quando"]
    origem = viagem.get("origem", "Garagem")
    if proxima.get("proximo_dia_util"):
        return f"{quando.strftime('%d/%m')} às {viagem['hora']} — {origem}"
    return f"{viagem['hora']} — {origem}"


def _viagem_atual_e_bloco(estado, agora):
    viagem = viagem_por_referencia(estado) or ultima_saida_oficial(agora)
    if not viagem:
        return None, None, None
    indice_bloco, bloco = _bloco_da_viagem(viagem.get("hora"))
    return viagem, indice_bloco, bloco


def _eh_ultima_volta(estado, agora):
    viagem, indice_bloco, bloco = _viagem_atual_e_bloco(estado, agora)
    if not viagem or not bloco or viagem.get("hora") != bloco.get("ultima"):
        return False, viagem, indice_bloco, bloco
    return True, viagem, indice_bloco, bloco


def _fase_final_ultima_volta(estado, agora):
    ultima, viagem, indice_bloco, bloco = _eh_ultima_volta(estado, agora)
    if not ultima:
        return False, viagem, indice_bloco, bloco

    ponto = (estado or {}).get("ponto_atual")
    resultado = (estado or {}).get("resultado_rota") or {}
    if ponto not in PONTOS_FINAIS_GARAGEM:
        return False, viagem, indice_bloco, bloco

    if ponto == "ru":
        # RU só representa a etapa final quando é a chegada de retorno, isto é,
        # quando não existe próximo ponto da rota normal após essa ocorrência.
        if resultado.get("ponto_atual_id") != "ru" or resultado.get("proximo") is not None:
            return False, viagem, indice_bloco, bloco
        return True, viagem, indice_bloco, bloco

    if ponto in {"fitotecnia", "solos_neas_florestal"}:
        return resultado.get("sentido") == "GARAGEM", viagem, indice_bloco, bloco

    if ponto == "garagem":
        return True, viagem, indice_bloco, bloco

    return False, viagem, indice_bloco, bloco


def _contexto_ultima_volta(estado, agora):
    ultima, _, indice_bloco, _ = _eh_ultima_volta(estado, agora)
    if not ultima:
        return ""

    proxima_txt = _formatar_proxima(_proxima_saida_apos_bloco(indice_bloco, agora))
    if not proxima_txt:
        return ""

    return (
        "🏁 Esta é a última volta deste bloco.\n"
        "🅿️ Depois desta volta, o circular segue para a Garagem.\n"
        f"⏰ Próxima saída: {proxima_txt}."
    )


def _ajustar_ru_da_ultima_volta(texto, estado, agora):
    """No RU de retorno da última volta, informa o percurso final à Garagem."""
    fase_final, _, _, _ = _fase_final_ultima_volta(estado, agora)
    if not fase_final or (estado or {}).get("ponto_atual") != "ru":
        return texto

    substituto = (
        "📍 Chegada ao RU confirmada.\n"
        "🏁 Última volta do bloco — sentido Garagem.\n"
        "↩️ O circular ainda pode passar por Fitotecnia e Solos antes de chegar à Garagem."
    )
    textos_antigos = [
        "🏁 Fim da volta confirmado no RU.",
        (
            "📍 Chegada ao RU confirmada.\n"
            "↩️ Na última volta do bloco, o circular ainda pode seguir por Fitotecnia e Solos antes da Garagem."
        ),
    ]
    for antigo in textos_antigos:
        texto = texto.replace(antigo, substituto)
    return texto


def _resumo_fase_final(estado, agora):
    fase_final, viagem, indice_bloco, _ = _fase_final_ultima_volta(estado, agora)
    if not fase_final or not viagem:
        return None

    proxima_txt = _formatar_proxima(_proxima_saida_apos_bloco(indice_bloco, agora))
    if not proxima_txt:
        return None

    ponto = (estado or {}).get("ponto_atual")
    resultado = (estado or {}).get("resultado_rota") or {}
    linhas = [
        "🚌 <b>Circular UFRB — Principal</b>",
        "",
        f"🏁 <b>Última volta do bloco — {viagem['hora']}</b>",
        "🅿️ <b>Etapa final / sentido Garagem</b>",
    ]

    if ponto == "ru":
        linhas.append("📍 Chegada ao RU confirmada; ainda pode passar por Fitotecnia e Solos.")
    elif ponto == "fitotecnia":
        linhas.append("📍 Última confirmação: Fitotecnia — seguindo para a Garagem.")
    elif ponto == "solos_neas_florestal":
        linhas.append("📍 Última confirmação: Solos / NEAS / Eng. Florestal — seguindo para a Garagem.")
    elif ponto == "garagem" or resultado.get("garagem_confirmada"):
        linhas.append("📍 Circular na Garagem.")

    linhas += [
        "",
        f"⏰ <b>Próxima volta: {proxima_txt}</b>",
    ]
    return "\n".join(linhas)


def _resumo_bloco_encerrado(estado, agora):
    resultado = (estado or {}).get("resultado_rota") or {}
    if not resultado.get(MARCADOR_FIM_BLOCO):
        return None

    ultima = resultado.get("ultima_volta")
    indice_bloco, bloco = _bloco_da_viagem(ultima)
    if bloco is None:
        return None

    proxima_txt = _formatar_proxima(_proxima_saida_apos_bloco(indice_bloco, agora))
    if not proxima_txt:
        return None

    garagem = (
        "🅿️ Circular na Garagem."
        if resultado.get("garagem_confirmada")
        else "🅿️ Circular provavelmente na Garagem."
    )
    return (
        "🚌 <b>Circular UFRB — Principal</b>\n\n"
        f"🏁 A volta das <b>{ultima}</b> já encerrou.\n"
        f"{garagem}\n\n"
        f"⏰ Próxima volta: <b>{proxima_txt}</b>"
    )


class BusState(_entry.BusState):
    async def localizacao(self):
        resposta = await super().localizacao()
        estado = await self._carregar()
        agora = _entry.agora_local()

        resposta["texto"] = _ajustar_ru_da_ultima_volta(
            resposta.get("texto", ""), estado, agora
        )

        status = await self.status_registro_principal()
        if not status.get("ativo"):
            return resposta

        contexto = _contexto_ultima_volta(estado, agora)
        if not contexto:
            return resposta

        texto = resposta.get("texto", "")
        linha_antiga = "🅿️ Sem nova saída neste bloco; o circular provavelmente segue para a Garagem."
        if linha_antiga in texto:
            texto = texto.replace(linha_antiga, contexto)
        elif contexto not in texto:
            texto += "\n\n" + contexto

        resposta["texto"] = texto
        return resposta

    async def resumo_horarios(self):
        # Primeiro deixa a lógica central atualizar/persistir o estado. Depois,
        # a etapa final da última volta substitui "volta em andamento" por um
        # estado de encerramento; se o bloco já fechou, o marcador tem prioridade.
        resposta = await super().resumo_horarios()
        estado = await self._carregar()
        agora = _entry.agora_local()

        encerrado = _resumo_bloco_encerrado(estado, agora)
        if encerrado:
            return {"texto": encerrado}

        fase_final = _resumo_fase_final(estado, agora)
        if fase_final:
            return {"texto": fase_final}

        return resposta


class Default(_entry.Default):
    pass
