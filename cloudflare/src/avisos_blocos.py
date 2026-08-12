from datetime import timedelta

from dados import HORARIOS

LIMITE_INTERVALO_BLOCO_MINUTOS = 60


def _minutos(hora):
    hh, mm = map(int, hora.split(":"))
    return hh * 60 + mm


def _grupos_horarios():
    horarios = HORARIOS["principal"]
    if not horarios:
        return []

    grupos = [[horarios[0]]]
    for anterior, atual in zip(horarios, horarios[1:]):
        intervalo = _minutos(atual["hora"]) - _minutos(anterior["hora"])
        if intervalo > LIMITE_INTERVALO_BLOCO_MINUTOS:
            grupos.append([])
        grupos[-1].append(atual)
    return grupos


def _momento(hora, referencia):
    hh, mm = map(int, hora.split(":"))
    return referencia.replace(hour=hh, minute=mm, second=0, microsecond=0)


def _fim_hora_da_ultima_saida(grupo, referencia):
    ultima = _momento(grupo[-1]["hora"], referencia)
    # O aviso dura ate o fim da faixa horaria da ultima saida do bloco.
    # 07:55 -> 08:00 | 10:00 -> 11:00 | 18:15 -> 19:00.
    return ultima.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


def expiracao_bloco_aviso(agora):
    """Retorna quando um aviso criado agora deve expirar.

    Se o aviso for criado pouco antes do primeiro horario de um bloco, ele
    pertence ao proximo bloco. Se estiver entre blocos, tambem e associado ao
    proximo bloco disponivel. Depois da ultima faixa do dia, expira no fim da
    hora da ultima saida.
    """
    grupos = _grupos_horarios()
    if not grupos:
        return agora + timedelta(hours=1)

    for grupo in grupos:
        fim = _fim_hora_da_ultima_saida(grupo, agora)
        if agora < fim:
            return fim

    return _fim_hora_da_ultima_saida(grupos[-1], agora)
