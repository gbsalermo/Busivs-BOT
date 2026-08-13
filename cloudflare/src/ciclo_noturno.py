from datetime import datetime

from dados import BLOCOS_PRINCIPAL
from regras import agora_local, estado_vazio

INICIO_TURNO_NOTURNO = "20:40"


def _minutos(hora):
    hh, mm = map(int, hora.split(":"))
    return hh * 60 + mm


def _dt(valor):
    return datetime.fromisoformat(valor) if valor else None


def _previsto(hora, agora):
    hh, mm = map(int, hora.split(":"))
    return agora.replace(hour=hh, minute=mm, second=0, microsecond=0)


def ultimo_inicio_de_ciclo_noturno(agora=None):
    """Retorna o último bloco noturno iniciado.

    20:40, 21:40 e 22:30 pertencem ao mesmo turno da noite, mas cada horário
    abre um bloco operacional independente que sai e retorna à Garagem.
    """
    agora = agora or agora_local()
    limite = _minutos(INICIO_TURNO_NOTURNO)
    candidatos = []

    for bloco in BLOCOS_PRINCIPAL:
        if _minutos(bloco["inicio"]) < limite:
            continue
        inicio = _previsto(bloco["inicio"], agora)
        if inicio <= agora:
            candidatos.append(inicio)

    return max(candidatos) if candidatos else None


def reiniciar_se_novo_ciclo_noturno(estado, agora=None):
    agora = agora or agora_local()
    horario_estado = _dt(estado.get("horario"))
    if not horario_estado:
        return estado

    inicio_ciclo = ultimo_inicio_de_ciclo_noturno(agora)
    if inicio_ciclo and horario_estado < inicio_ciclo:
        return estado_vazio()

    return estado
