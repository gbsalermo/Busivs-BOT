from datetime import datetime, timedelta

from dados import BLOCOS_PRINCIPAL, HORARIOS
from regras import estimar_chegada_portao_1

TOLERANCIA_RETORNO_DIA_MINUTOS = 15
TOLERANCIA_RETORNO_NOITE_MINUTOS = 10
EXTENSAO_PICO_POR_CONFIRMACAO_MINUTOS = 10
SOBREPOSICAO_MAXIMA_PROXIMO_BLOCO_MINUTOS = 5
JANELA_CONFIRMACAO_PICO_MINUTOS = 15


def _momento(hora, referencia):
    hh, mm = map(int, hora.split(":"))
    return referencia.replace(hour=hh, minute=mm, second=0, microsecond=0)


def _viagem_por_hora(hora):
    for viagem in HORARIOS.get("principal", []):
        if viagem["hora"] == hora:
            return viagem
    return None


def blocos_no_dia(referencia):
    blocos = []
    for i, definicao in enumerate(BLOCOS_PRINCIPAL):
        inicio = _momento(definicao["inicio"], referencia)
        ultima = _viagem_por_hora(definicao["ultima"])
        if ultima is None:
            continue

        previsao = estimar_chegada_portao_1(ultima["hora"])
        fim_p1 = _momento(previsao["fim"], referencia)
        tolerancia = (
            TOLERANCIA_RETORNO_NOITE_MINUTOS
            if previsao.get("noturno")
            else TOLERANCIA_RETORNO_DIA_MINUTOS
        )
        fim_base = fim_p1 + timedelta(minutes=tolerancia)

        proximo_inicio = None
        proxima_viagem = None
        if i + 1 < len(BLOCOS_PRINCIPAL):
            proxima_definicao = BLOCOS_PRINCIPAL[i + 1]
            proximo_inicio = _momento(proxima_definicao["inicio"], referencia)
            proxima_viagem = _viagem_por_hora(proxima_definicao["inicio"])

        blocos.append({
            **definicao,
            "inicio_dt": inicio,
            "ultima_viagem": ultima,
            "previsao_p1": previsao,
            "fim_p1": fim_p1,
            "fim_base": fim_base,
            "proximo_inicio": proximo_inicio,
            "proxima_viagem": proxima_viagem,
            "pico": bool(previsao.get("pico")),
            "noturno": bool(previsao.get("noturno")),
        })
    return blocos


def bloco_para_aviso(agora):
    """Escolhe o único bloco ao qual um aviso operacional deve pertencer."""
    blocos = blocos_no_dia(agora)

    ativos = [b for b in blocos if b["inicio_dt"] <= agora < b["fim_base"]]
    if ativos:
        return max(ativos, key=lambda b: b["inicio_dt"])

    proximos = [b for b in blocos if b["inicio_dt"] > agora]
    if proximos:
        return min(proximos, key=lambda b: b["inicio_dt"])

    return blocos[-1] if blocos else None


def expiracao_aviso_do_bloco(agora):
    bloco = bloco_para_aviso(agora)
    if bloco is None:
        return agora + timedelta(hours=1)
    return bloco["fim_base"]


def _confirmacao_estado(estado):
    valor = (estado or {}).get("horario")
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return None


def fim_efetivo_bloco(bloco, estado=None):
    """Fecha o bloco por estimativa, com extensão curta quando o pico atrasou.

    Uma confirmação real perto do fechamento pode estender um bloco de pico em
    até 10 min. Se já existe bloco seguinte, o estado antigo pode sobreviver no
    máximo 5 min dentro dele; uma confirmação compatível com a nova saída passa
    então a representar o bloco novo.
    """
    fim = bloco["fim_base"]
    confirmado_em = _confirmacao_estado(estado)

    if not bloco.get("pico") or confirmado_em is None:
        return fim
    if confirmado_em.date() != fim.date():
        return fim

    inicio_janela = fim - timedelta(minutes=JANELA_CONFIRMACAO_PICO_MINUTOS)
    if confirmado_em < inicio_janela:
        return fim

    extendido = max(
        fim,
        confirmado_em + timedelta(minutes=EXTENSAO_PICO_POR_CONFIRMACAO_MINUTOS),
    )

    proximo = bloco.get("proximo_inicio")
    if proximo is not None:
        limite = proximo + timedelta(minutes=SOBREPOSICAO_MAXIMA_PROXIMO_BLOCO_MINUTOS)
        extendido = min(extendido, limite)

    return extendido


def contexto_bloco_encerrado(estado, agora):
    """Retorna a lacuna em que o bloco anterior já voltou à Garagem."""
    for bloco in blocos_no_dia(agora):
        fim = fim_efetivo_bloco(bloco, estado)
        proximo = bloco.get("proximo_inicio")

        if agora < fim:
            continue
        if proximo is not None and agora >= proximo:
            continue

        return {
            "bloco": bloco,
            "fim_previsto": fim,
            "proxima": bloco.get("proxima_viagem"),
            "fim_do_dia": proximo is None,
        }

    return None
