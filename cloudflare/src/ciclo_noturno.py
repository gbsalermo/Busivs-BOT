from datetime import datetime

from dados import HORARIOS
from regras import agora_local, estado_vazio

INICIO_CICLOS_NOTURNOS = "20:40"


def _minutos(hora):
    hh, mm = map(int, hora.split(":"))
    return hh * 60 + mm


def _dt(valor):
    return datetime.fromisoformat(valor) if valor else None


def _previsto(hora, agora):
    hh, mm = map(int, hora.split(":"))
    return agora.replace(hour=hh, minute=mm, second=0, microsecond=0)


def ultimo_inicio_de_ciclo_noturno(agora=None):
    agora = agora or agora_local()
    limite = _minutos(INICIO_CICLOS_NOTURNOS)
    candidatos = []

    for horario in HORARIOS["principal"]:
        if _minutos(horario["hora"]) < limite:
            continue
        inicio = _previsto(horario["hora"], agora)
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
