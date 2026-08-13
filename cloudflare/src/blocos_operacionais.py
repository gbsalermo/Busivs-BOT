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
        if i + 1 < len(BLOCOS_PRINCIPAL):
            proximo_inicio = _momento(BLOCOS_PRINCIPAL[i + 1]["inicio"], referencia)

        blocos.append({
            **definicao,
            "inicio_dt": inicio,
            "ultima_viagem": ultima,
            "previsao_p1": previsao,
            "fim_p1": fim_p1,
            "fim_base": fim_base,
            "proximo_inicio": proximo_inicio,
            "pico": bool(previsao.get("pico")),
            "noturno": bool(previsao.get("noturno")),
        })
    return blocos


def bloco_por_inicio(hora, referencia):
    for bloco in blocos_no_dia(referencia):
        if bloco["inicio"] == hora:
            return bloco
    return None


def bloco_da_ultima_saida(agora):
    candidatos = [b for b in blocos_no_dia(agora) if b["inicio_dt"] <= agora]
    return max(candidatos, key=lambda b: b["inicio_dt"]) if candidatos else None


def bloco_para_aviso(agora):
    """Escolhe o bloco ao qual um aviso operacional deve pertencer.

    Se ainda estamos dentro da janela estimada do bloco corrente, usa esse
    bloco. Se o bloco já encerrou e estamos numa lacuna, o aviso passa a valer
    para o próximo bloco. Assim nenhum aviso atravessa dois blocos.
    """
    blocos = blocos_no_dia(agora)
    atual = None
    for bloco in blocos:
        if bloco["inicio_dt"] <= agora < bloco["fim_base"]:
            atual = bloco
    if atual:
        return atual

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
    """Retorna o fechamento estimado, com pequena extensão em horário de pico.

    A extensão só existe quando há confirmação real recente perto do fechamento.
    Mesmo assim, ela é limitada para não carregar indefinidamente o bloco antigo
    para dentro do próximo: no máximo 5 min após a abertura do bloco seguinte.
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

    extendido = max(fim, confirmado_em + timedelta(minutes=EXTENSAO_PICO_POR_CONFIRMACAO_MINUTOS))
    proximo = bloco.get("proximo_inicio")
    if proximo is not None:
        limite = proximo + timedelta(minutes=SOBREPOSICAO_MAXIMA_PROXIMO_BLOCO_MINUTOS)
        extendido = min(extendido, limite)

    return extendido


def contexto_bloco_encerrado(estado, agora):
    """Indica quando um bloco já terminou e ainda não começou o próximo.

    Em pico, uma confirmação recente pode estender brevemente o bloco. Se o
    próximo bloco já começou, o estado antigo deixa de ser tratado como
    'garagem aguardando' e passa a ser resolvido pelas regras da nova saída.
    """
    blocos = blocos_no_dia(agora)
    for bloco in blocos:
        fim = fim_efetivo_bloco(bloco, estado)
        proximo = bloco.get("proximo_inicio")

        if agora < fim:
            continue

        if proximo is not None and agora >= proximo:
            continue

        return {
            "bloco": bloco,
            "fim_previsto": fim,
            "proxima": (
                _viagem_por_hora(BLOCOS_PRINCIPAL[BLOCOS_PRINCIPAL.index(next(d for d in BLOCOS_PRINCIPAL if d["id"] == bloco["id"])) + 1]["inicio"])
                if proximo is not None
                else None
            ),
            "fim_do_dia": proximo is None,
        }

    return None
