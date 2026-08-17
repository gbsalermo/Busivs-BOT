from datetime import datetime, timedelta

from dados import HORARIOS
from regras import estimar_chegada_portao_1

JANELA_RU_REFERENCIA_MINUTOS = 15
JANELA_TRANSICAO_PROVAVEL_MINUTOS = 10
LIMITE_REFERENCIA_SEM_CONFIRMACAO_MINUTOS = 15


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


def _confirmacao_sustenta_referencia_atual(estado, proxima, agora):
    confirmado_em = _confirmacao_em(estado)
    if confirmado_em is None or confirmado_em.date() != agora.date():
        return False
    saida_proxima = _momento(proxima["hora"], agora)
    return confirmado_em >= saida_proxima


def proxima_volta_provavel(estado, agora):
    atual = viagem_por_referencia(estado)
    proxima = proxima_apos_referencia(estado)
    if atual is None or proxima is None:
        return None

    confirmado_em = _confirmacao_em(estado)
    saida_proxima = _momento(proxima["hora"], agora)
    if agora < saida_proxima:
        return None

    resultado = (estado or {}).get("resultado_rota") or {}
    retorno_claro = resultado.get("sentido") == "RU"

    # Caso forte: há confirmação clara de retorno. Dez minutos depois dessa
    # confirmação (e nunca antes da próxima saída oficial), a próxima volta já
    # pode ser exibida como provavelmente em andamento.
    if retorno_claro and confirmado_em is not None and confirmado_em.date() == agora.date():
        liberacao_retorno = max(
            saida_proxima,
            confirmado_em + timedelta(minutes=JANELA_TRANSICAO_PROVAVEL_MINUTOS),
        )
        if agora >= liberacao_retorno:
            return {
                "viagem_anterior": atual,
                "viagem_provavel": proxima,
                "confirmado_em": confirmado_em,
                "liberado_em": liberacao_retorno,
                "ponto_id": (estado or {}).get("ponto_atual"),
                "motivo": "retorno_confirmado",
            }

    # Segurança geral: uma referência, inclusive manual, nunca congela a grade.
    # Sem confirmação nova após o horário da próxima saída, ela perde força no
    # máximo 15 minutos depois e a próxima volta passa a ser provável. Isso
    # mantém o comportamento automático mesmo quando não houve voto no retorno.
    limite = saida_proxima + timedelta(minutes=LIMITE_REFERENCIA_SEM_CONFIRMACAO_MINUTOS)
    if agora >= limite and not _confirmacao_sustenta_referencia_atual(estado, proxima, agora):
        return {
            "viagem_anterior": atual,
            "viagem_provavel": proxima,
            "confirmado_em": confirmado_em,
            "liberado_em": limite,
            "ponto_id": (estado or {}).get("ponto_atual"),
            "motivo": "limite_sem_confirmacao",
        }

    return None


def resumo_referenciado(estado, agora, resumo_padrao):
    atual = viagem_por_referencia(estado)
    if atual is None:
        return resumo_padrao

    previsao = estimar_chegada_portao_1(atual["hora"])
    proxima = proxima_apos_referencia(estado)
    provavel = proxima_volta_provavel(estado, agora)
    manual = bool((estado or {}).get("saida_referencia_manual"))
    origem = atual.get("origem", "")
    modo = "ajustada manualmente pelo administrador" if manual else "fixada pelas confirmações de passagem"

    if provavel:
        viagem = provavel["viagem_provavel"]
        p = estimar_chegada_portao_1(viagem["hora"])
        motivo = provavel.get("motivo")
        if motivo == "retorno_confirmado":
            explicacao = [
                "⬅️ A última confirmação indicava o ônibus no percurso de retorno.",
                f"🕐 Já passaram pelo menos {JANELA_TRANSICAO_PROVAVEL_MINUTOS} min desde essa confirmação.",
            ]
        else:
            explicacao = [
                "⏱️ A referência anterior atingiu o limite operacional sem nova confirmação.",
                f"🕐 Já passaram {LIMITE_REFERENCIA_SEM_CONFIRMACAO_MINUTOS} min da próxima saída oficial.",
            ]
        return "\n".join([
            "🚌 <b>Circular UFRB — Principal</b>",
            "",
            "🟡 <b>Próxima volta provavelmente em andamento</b>",
            f"🕐 Referência provável: <b>{viagem['hora']}</b> — {viagem.get('origem', '')}",
            f"🚪 Referência do Portão 1: <b>{p['inicio']}–{p['fim']}</b>",
            "",
            f"📌 Última volta confirmada: <b>{atual['hora']}</b> — {origem}",
            *explicacao,
            "ℹ️ A nova volta é uma inferência operacional, não uma confirmação de passagem.",
        ])

    linhas = [
        "🚌 <b>Circular UFRB — Principal</b>",
        "",
        "🔵 <b>Volta confirmada em andamento</b>",
        f"🕐 Referência: <b>{atual['hora']}</b> — {origem}",
        f"🚪 Referência do Portão 1: <b>{previsao['inicio']}–{previsao['fim']}</b>",
        f"📌 Esta referência está {modo}.",
        "ℹ️ Ela continua valendo enquanto ainda estiver dentro da janela operacional ou houver confirmação que a sustente.",
    ]

    if proxima:
        linhas += [
            "",
            "🟢 <b>Próxima saída oficial</b>",
            f"🕐 <b>{proxima['hora']}</b> — {proxima.get('origem', '')}",
            "⚠️ Se a volta atual estiver atrasada, essa saída também pode sofrer atraso.",
        ]

    return "\n".join(linhas)