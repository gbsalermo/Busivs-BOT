from datetime import datetime, timedelta

from dados import BLOCOS_PRINCIPAL, HORARIOS
from regras import estimar_chegada_portao_1

JANELA_RU_REFERENCIA_MINUTOS = 10
LIMITE_REFERENCIA_APOS_PROXIMA_MINUTOS = 15

ETA_RETORNO_RU_MINUTOS = {
    "ponto_externo_2": 25,
    "portao_1": 20,
    "biblioteca": 10,
    "torre_cotec": 5,
    "ru": 2,
}


def _momento(hora, referencia):
    hh, mm = map(int, hora.split(":"))
    return referencia.replace(hour=hh, minute=mm, second=0, microsecond=0)


def _origem_ru(viagem):
    origem = (viagem or {}).get("origem", "").strip().lower()
    return "ru" in origem or "resid" in origem


def _indice_hora(hora):
    for i, viagem in enumerate(HORARIOS.get("principal", [])):
        if viagem.get("hora") == hora:
            return i
    return None


def _bloco_da_viagem(hora):
    if not hora:
        return None
    minuto = int(hora[:2]) * 60 + int(hora[3:5])
    for bloco in BLOCOS_PRINCIPAL:
        ini = int(bloco["inicio"][:2]) * 60 + int(bloco["inicio"][3:5])
        fim = int(bloco["ultima"][:2]) * 60 + int(bloco["ultima"][3:5])
        if ini <= minuto <= fim:
            return bloco
    return None


def viagem_por_referencia(estado):
    hora = (estado or {}).get("saida_referencia")
    if not hora:
        return None
    indice = _indice_hora(hora)
    if indice is None:
        return None
    return HORARIOS["principal"][indice]


def ultima_saida_oficial(agora):
    candidatas = []
    for viagem in HORARIOS.get("principal", []):
        momento = _momento(viagem["hora"], agora)
        if momento <= agora:
            candidatas.append((momento, viagem))
    return max(candidatas, key=lambda item: item[0])[1] if candidatas else None


def saida_ru_recente(agora):
    candidatas = []
    for viagem in HORARIOS.get("principal", []):
        if not _origem_ru(viagem):
            continue
        momento = _momento(viagem["hora"], agora)
        atraso = agora - momento
        if timedelta(0) <= atraso <= timedelta(minutes=JANELA_RU_REFERENCIA_MINUTOS):
            candidatas.append((momento, viagem))
    return max(candidatas, key=lambda item: item[0])[1] if candidatas else None


def aplicar_referencia(estado, viagem, manual=False):
    if not estado or not viagem:
        return estado
    estado["saida_referencia"] = viagem["hora"]
    estado["saida_referencia_manual"] = bool(manual)
    return estado


def retornar_volta_anterior(estado, agora):
    horarios = HORARIOS.get("principal", [])
    atual = viagem_por_referencia(estado) or ultima_saida_oficial(agora)
    if atual is None:
        return estado, None
    indice = _indice_hora(atual["hora"])
    if indice is None or indice <= 0:
        return estado, None
    anterior = horarios[indice - 1]
    aplicar_referencia(estado, anterior, manual=True)
    return estado, anterior


def proxima_apos_referencia(estado):
    viagem = viagem_por_referencia(estado)
    if viagem is None:
        return None
    indice = _indice_hora(viagem["hora"])
    if indice is None or indice + 1 >= len(HORARIOS["principal"]):
        return None
    return HORARIOS["principal"][indice + 1]


def _confirmacao_em(estado):
    valor = (estado or {}).get("horario")
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return None


def _liberacao_por_retorno(estado, agora, proxima):
    resultado = (estado or {}).get("resultado_rota") or {}
    if resultado.get("sentido") != "RU":
        return None
    ponto_id = (estado or {}).get("ponto_atual")
    eta = ETA_RETORNO_RU_MINUTOS.get(ponto_id)
    if eta is None:
        return None
    confirmado_em = _confirmacao_em(estado)
    if confirmado_em is None or confirmado_em.date() != agora.date():
        return None
    saida_proxima = _momento(proxima["hora"], agora)
    return max(saida_proxima, confirmado_em + timedelta(minutes=eta))


def limite_referencia(estado, agora):
    atual = viagem_por_referencia(estado)
    proxima = proxima_apos_referencia(estado)
    if atual is None or proxima is None:
        return None
    saida_proxima = _momento(proxima["hora"], agora)
    teto = saida_proxima + timedelta(minutes=LIMITE_REFERENCIA_APOS_PROXIMA_MINUTOS)
    retorno = _liberacao_por_retorno(estado, agora, proxima)
    if retorno is not None:
        return min(retorno, teto)
    return teto


def referencia_ainda_valida(estado, agora):
    atual = viagem_por_referencia(estado)
    if atual is None:
        return False
    limite = limite_referencia(estado, agora)
    return limite is None or agora < limite


def proxima_volta_provavel(estado, agora):
    atual = viagem_por_referencia(estado)
    proxima = proxima_apos_referencia(estado)
    if atual is None or proxima is None:
        return None
    limite = limite_referencia(estado, agora)
    if limite is None or agora < limite:
        return None
    retorno = _liberacao_por_retorno(estado, agora, proxima)
    return {
        "viagem_anterior": atual,
        "viagem_provavel": proxima,
        "confirmado_em": _confirmacao_em(estado),
        "liberado_em": limite,
        "ponto_id": (estado or {}).get("ponto_atual"),
        "por_retorno": retorno is not None and limite == min(
            retorno,
            _momento(proxima["hora"], agora) + timedelta(minutes=LIMITE_REFERENCIA_APOS_PROXIMA_MINUTOS),
        ),
    }


def limpar_referencia_expirada(estado, agora):
    if not estado or referencia_ainda_valida(estado, agora):
        return estado
    estado.pop("saida_referencia", None)
    estado.pop("saida_referencia_manual", None)
    return estado


def resumo_referenciado(estado, agora, resumo_padrao):
    atual = viagem_por_referencia(estado)
    if atual is None:
        return resumo_padrao

    provavel = proxima_volta_provavel(estado, agora)
    if provavel:
        viagem = provavel["viagem_provavel"]
        p = estimar_chegada_portao_1(viagem["hora"])
        linhas = [
            "🚌 <b>Circular UFRB — Principal</b>",
            "",
            "🟡 <b>Próxima volta provavelmente em andamento</b>",
            f"🕐 Referência provável: <b>{viagem['hora']}</b> — {viagem.get('origem', '')}",
            f"🚪 Referência do Portão 1: <b>{p['inicio']}–{p['fim']}</b>",
            "",
            f"📌 Última volta confirmada: <b>{atual['hora']}</b> — {atual.get('origem', '')}",
        ]
        return "\n".join(linhas)

    previsao = estimar_chegada_portao_1(atual["hora"])
    proxima = proxima_apos_referencia(estado)
    origem = atual.get("origem", "")
    bloco_atual = _bloco_da_viagem(atual["hora"])
    ultima_do_bloco = bool(bloco_atual and bloco_atual.get("ultima") == atual.get("hora"))

    linhas = [
        "🚌 <b>Circular UFRB — Principal</b>",
        "",
        "🔵 <b>Volta confirmada em andamento</b>",
        f"🕐 Referência: <b>{atual['hora']}</b> — {origem}",
        f"🚪 Referência do Portão 1: <b>{previsao['inicio']}–{previsao['fim']}</b>",
    ]

    if ultima_do_bloco:
        linhas.append("🏁 <b>Esta é a última volta deste bloco operacional.</b>")

    if proxima:
        proximo_bloco = _bloco_da_viagem(proxima["hora"])
        linhas += [
            "",
            "🟢 <b>Próxima saída oficial</b>",
            f"🕐 <b>{proxima['hora']}</b> — {proxima.get('origem', '')}",
        ]
        if (
            ultima_do_bloco
            and proximo_bloco
            and bloco_atual
            and proximo_bloco.get("id") != bloco_atual.get("id")
        ):
            linhas.append("📦 Essa próxima saída já pertence ao próximo bloco operacional.")

    return "\n".join(linhas)
