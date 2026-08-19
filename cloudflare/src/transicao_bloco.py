from datetime import datetime, timedelta

from blocos_operacionais import blocos_no_dia
from dados import BLOCOS_PRINCIPAL, HORARIOS, ROTA
from regras import estimar_chegada_portao_1

MARGEM_RETORNO_MINUTOS = 5
JANELA_RU_NOVA_VOLTA_MINUTOS = 15


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


def _origem_ru(viagem):
    origem = (viagem or {}).get("origem", "").strip().lower()
    return "ru" in origem or "resid" in origem


def _ultima_saida_ru_recente(agora):
    candidatas = []
    for viagem in HORARIOS.get("principal", []):
        if not _origem_ru(viagem):
            continue
        saida = _momento(viagem["hora"], agora)
        if saida <= agora and agora - saida <= timedelta(minutes=JANELA_RU_NOVA_VOLTA_MINUTOS):
            candidatas.append((saida, viagem))
    return max(candidatas, key=lambda item: item[0]) if candidatas else None


def _indice_hora(hora):
    for indice, viagem in enumerate(HORARIOS.get("principal", [])):
        if viagem.get("hora") == hora:
            return indice
    return None


def _ru_finalizou_volta(estado):
    if (estado or {}).get("ponto_atual") != "ru":
        return False
    resultado = (estado or {}).get("resultado_rota") or {}
    return resultado.get("ponto_atual_id") == "ru" and resultado.get("proximo") is None


def _existe_saida_posterior_a_referencia(estado, agora):
    referencia = (estado or {}).get("saida_referencia")
    indice = _indice_hora(referencia)
    if indice is None:
        return False
    for viagem in HORARIOS.get("principal", [])[indice + 1:]:
        if _momento(viagem["hora"], agora) <= agora:
            return True
    return False


def _ru_inicia_nova_volta(estado, agora):
    """Reconhece RU como início de uma nova saída oficial próxima.

    Uma referência escolhida manualmente pelo administrador é autoritativa:
    enquanto ela estiver marcada como manual, uma confirmação no RU representa
    o fechamento/continuação daquela volta e não pode ser promovida apenas pelo
    relógio para a saída oficial mais recente.
    """
    confirmado_em = _confirmado_em(estado)
    if confirmado_em is None or confirmado_em.date() != agora.date():
        return False

    if (estado or {}).get("saida_referencia_manual"):
        return False

    recente = _ultima_saida_ru_recente(agora)
    if recente is None:
        return False

    saida, viagem = recente
    referencia_estado = (estado or {}).get("saida_referencia")

    if referencia_estado == viagem["hora"]:
        return False

    if confirmado_em < saida:
        return True

    if referencia_estado:
        return referencia_estado != viagem["hora"]

    return False


def _ponto_compativel(ponto_id, bloco, agora):
    ocorrencias = [i for i, item in enumerate(ROTA) if item["ponto_id"] == ponto_id]
    if not ocorrencias:
        return False

    if ponto_id == "ru":
        return False

    if ponto_id == "biblioteca":
        return True

    if ponto_id not in {"portao_1", "torre_cotec"}:
        return True

    referencia = _ultima_referencia(bloco, agora)
    if referencia is None:
        return False

    inicio, viagem = referencia
    previsao = estimar_chegada_portao_1(viagem["hora"])
    chegada_min = _momento(previsao["inicio"], agora)
    liberacao = chegada_min - timedelta(minutes=MARGEM_RETORNO_MINUTOS)
    return agora >= max(inicio, liberacao)


def _bloco_da_ultima_saida(agora):
    viagens = [v for v in HORARIOS.get("principal", []) if _momento(v["hora"], agora) <= agora]
    if not viagens:
        return None
    ultima = max(viagens, key=lambda v: _momento(v["hora"], agora))
    minuto = int(ultima["hora"][:2]) * 60 + int(ultima["hora"][3:5])
    for bloco in BLOCOS_PRINCIPAL:
        ini = int(bloco["inicio"][:2]) * 60 + int(bloco["inicio"][3:5])
        fim = int(bloco["ultima"][:2]) * 60 + int(bloco["ultima"][3:5])
        if ini <= minuto <= fim:
            return bloco
    return None


def confirmacao_inicia_novo_bloco(estado, ponto_id, agora):
    """Retorna True quando a confirmação deve abandonar o histórico anterior.

    Referência manual dura até a volta realmente terminar no RU. Depois disso,
    uma confirmação em ponto de percurso após existir uma saída oficial mais
    nova libera a regra geral novamente. Isso também evita que o relógio, sozinho,
    sobrescreva a referência manual antes do fechamento real da volta.
    """
    confirmado_em = _confirmado_em(estado)
    if confirmado_em is None or confirmado_em.date() != agora.date():
        return False

    if ponto_id == "ru" and _ru_inicia_nova_volta(estado, agora):
        return True

    if (
        (estado or {}).get("saida_referencia_manual")
        and _ru_finalizou_volta(estado)
        and ponto_id != "ru"
        and _existe_saida_posterior_a_referencia(estado, agora)
    ):
        bloco = _bloco_da_ultima_saida(agora)
        if bloco is not None and _ponto_compativel(ponto_id, bloco, agora):
            return True

    candidatos = [
        bloco
        for bloco in blocos_no_dia(agora)
        if confirmado_em < bloco["inicio_dt"] <= agora
    ]
    if not candidatos:
        return False

    bloco_novo = max(candidatos, key=lambda bloco: bloco["inicio_dt"])
    return _ponto_compativel(ponto_id, bloco_novo, agora)
