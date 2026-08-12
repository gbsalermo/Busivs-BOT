from datetime import timedelta

from dados import HORARIOS
from regras import estado_vazio, estimar_chegada_portao_1


TOLERANCIA_PICO_MINUTOS = 5


def _horario_no_dia(hora, agora):
    hh, mm = map(int, hora.split(":"))
    return agora.replace(hour=hh, minute=mm, second=0, microsecond=0)


def expirar_confirmacao_pico(estado, agora):
    """Descarta confirmação de uma volta anterior após a tolerância de pico.

    Uma confirmação anterior ao horário de uma nova saída de pico ainda pode
    representar a volta anterior durante os primeiros cinco minutos. Depois
    dessa janela, se não houve nova confirmação, ela deixa de representar a
    localização atual do ônibus.
    """
    horario_estado = estado.get("horario")
    if not horario_estado:
        return estado

    try:
        from datetime import datetime
        confirmado_em = datetime.fromisoformat(horario_estado)
    except (TypeError, ValueError):
        return estado

    if confirmado_em.date() != agora.date():
        return estado_vazio()

    for viagem in HORARIOS["principal"]:
        previsao = estimar_chegada_portao_1(viagem["hora"])
        if not previsao.get("pico"):
            continue

        saida = _horario_no_dia(viagem["hora"], agora)
        fim_tolerancia = saida + timedelta(minutes=TOLERANCIA_PICO_MINUTOS)

        if confirmado_em < saida and agora >= fim_tolerancia:
            return estado_vazio()

    return estado
