from datetime import datetime, timedelta

from blocos_operacionais import blocos_no_dia
from dados import HORARIOS, ROTA
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


def _ru_inicia_nova_volta(estado, agora):
    """Reconhece RU como início de uma nova saída oficial próxima.

    Há dois casos válidos:
    1. a confirmação salva é anterior à nova saída do RU;
    2. a volta anterior chegou atrasada ao RU depois do horário oficial, mas o
       estado ainda carrega uma referência de volta mais antiga. Nesse caso o
       timestamp sozinho não basta: a referência antiga prova que um novo RU
       pode representar o início da saída mais recente.

    Se o estado já está referenciado na própria saída recente, não reiniciamos o
    contexto; isso evita transformar dois votos de RU da mesma volta em wraps.
    """
    confirmado_em = _confirmado_em(estado)
    if confirmado_em is None or confirmado_em.date() != agora.date():
        return False

    recente = _ultima_saida_ru_recente(agora)
    if recente is None:
        return False

    saida, viagem = recente
    referencia_estado = (estado or {}).get("saida_referencia")

    # O estado já pertence à saída atual: um novo RU não deve abrir outra volta.
    if referencia_estado == viagem["hora"]:
        return False

    # Caso clássico: a nova saída ocorreu depois da última confirmação salva.
    if confirmado_em < saida:
        return True

    # Caso de atraso/cascata: a confirmação anterior aconteceu depois do horário
    # oficial, mas ainda pertence explicitamente a uma referência mais antiga.
    if referencia_estado:
        return referencia_estado != viagem["hora"]

    return False


def _ponto_compativel(ponto_id, bloco, agora):
    ocorrencias = [i for i, item in enumerate(ROTA) if item["ponto_id"] == ponto_id]
    if not ocorrencias:
        return False

    # RU só troca o contexto aqui quando uma nova saída oficial do próprio RU
    # já foi detectada por _ru_inicia_nova_volta.
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


def confirmacao_inicia_novo_bloco(estado, ponto_id, agora):
    """Retorna True quando a confirmação deve abandonar o histórico anterior.

    Além de transições entre blocos, RU pode iniciar uma nova volta dentro do
    mesmo bloco quando uma nova saída oficial do RU ocorreu e o estado salvo
    ainda pertence a uma referência anterior.
    """
    confirmado_em = _confirmado_em(estado)
    if confirmado_em is None or confirmado_em.date() != agora.date():
        return False

    if ponto_id == "ru" and _ru_inicia_nova_volta(estado, agora):
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
