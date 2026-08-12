from datetime import datetime, timedelta

from dados import HORARIOS
from regras import estado_vazio


TOLERANCIA_NOVA_VOLTA_MINUTOS = 5


def _horario_no_dia(hora, agora):
    hh, mm = map(int, hora.split(":"))
    return agora.replace(hour=hh, minute=mm, second=0, microsecond=0)


def expirar_confirmacao_volta_anterior(estado, agora):
    """Descarta confirmação antiga após uma nova saída + tolerância.

    A regra vale para todos os blocos do dia, independentemente de ser horário
    de pico. Uma confirmação feita antes de uma nova saída oficial ainda pode
    representar a volta anterior durante os cinco minutos seguintes. Passada
    essa janela, se não houve uma nova confirmação, o ponto antigo deixa de
    representar a localização atual do ônibus.
    """
    horario_estado = estado.get("horario")
    if not horario_estado:
        return estado

    try:
        confirmado_em = datetime.fromisoformat(horario_estado)
    except (TypeError, ValueError):
        return estado

    if confirmado_em.date() != agora.date():
        return estado_vazio()

    # Procuramos a saída oficial mais recente que aconteceu depois da última
    # confirmação. Se a tolerância dessa saída já acabou, o estado é antigo.
    saidas_posteriores = []
    for viagem in HORARIOS["principal"]:
        saida = _horario_no_dia(viagem["hora"], agora)
        if confirmado_em < saida <= agora:
            saidas_posteriores.append(saida)

    if not saidas_posteriores:
        return estado

    ultima_saida = max(saidas_posteriores)
    fim_tolerancia = ultima_saida + timedelta(minutes=TOLERANCIA_NOVA_VOLTA_MINUTOS)

    if agora >= fim_tolerancia:
        return estado_vazio()

    return estado
