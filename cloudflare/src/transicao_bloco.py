from datetime import datetime, timedelta

from blocos_operacionais import blocos_no_dia
from dados import HORARIOS, ROTA
from regras import estimar_chegada_portao_1

MARGEM_RETORNO_MINUTOS = 5


def _momento(hora, referencia):
    hh, mm = map(int, hora.split(":"))
    return referencia.replace(hour=hh, minute=mm, second=0, microsecond=0)


def _confirmado_em(estado):
    valor = (estado or {}).get("horario")
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return None


def _viagens_do_bloco(bloco):
    horarios = HORARIOS.get("principal", [])
    inicio = next((i for i, h in enumerate(horarios) if h["hora"] == bloco["inicio"]), None)
    fim = next((i for i, h in enumerate(horarios) if h["hora"] == bloco["ultima"]), None)
    if inicio is None or fim is None or fim < inicio:
        return []
    return horarios[inicio:fim + 1]


def _ultima_referencia(bloco, agora):
    candidatas = []
    for viagem in _viagens_do_bloco(bloco):
        momento = _momento(viagem["hora"], agora)
        if momento <= agora:
            candidatas.append((momento, viagem))
    return max(candidatas, key=lambda item: item[0]) if candidatas else None


def _ponto_compativel(ponto_id, bloco, agora):
    ocorrencias = [i for i, item in enumerate(ROTA) if item["ponto_id"] == ponto_id]
    if not ocorrencias:
        return False

    # RU pode ser fim do bloco anterior ou espera; não usamos sozinho para trocar contexto.
    if ponto_id == "ru":
        return False

    # Biblioteca é o único ponto realmente ambíguo de sentido, mas ainda é
    # compatível com uma nova volta; a próxima confirmação resolve o sentido.
    if ponto_id == "biblioteca":
        return True

    # Pontos únicos da ida/rua já identificam naturalmente o novo contexto.
    if ponto_id not in {"portao_1", "torre_cotec"}:
        return True

    # Portão 1 e Torre/COTEC só podem pertencer ao bloco novo quando já houve
    # tempo plausível para o veículo alcançar o retorno.
    referencia = _ultima_referencia(bloco, agora)
    if referencia is None:
        return False

    inicio, viagem = referencia
    previsao = estimar_chegada_portao_1(viagem["hora"])
    chegada_min = _momento(previsao["inicio"], agora)
    liberacao = chegada_min - timedelta(minutes=MARGEM_RETORNO_MINUTOS)
    return agora >= max(inicio, liberacao)


def confirmacao_inicia_novo_bloco(estado, ponto_id, agora):
    """Retorna True quando o ponto novo deve abandonar todo o histórico anterior."""
    confirmado_em = _confirmado_em(estado)
    if confirmado_em is None or confirmado_em.date() != agora.date():
        return False

    candidatos = [
        bloco
        for bloco in blocos_no_dia(agora)
        if confirmado_em < bloco["inicio_dt"] <= agora
    ]
    if not candidatos:
        return False

    bloco_novo = max(candidatos, key=lambda bloco: bloco["inicio_dt"])
    return _ponto_compativel(ponto_id, bloco_novo, agora)
