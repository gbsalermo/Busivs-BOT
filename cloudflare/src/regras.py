import regras_base as _base


def _estimar_chegada_portao_1_sem_pico_13h(hora_saida):
    m = _base._minutos(hora_saida)
    pico = (
        hora_saida not in {"13:00", "13:25"}
        and (
            _base._minutos("07:30") <= m <= _base._minutos("08:00")
            or _base._minutos("11:30") <= m <= _base._minutos("14:00")
            or _base._minutos("17:30") <= m <= _base._minutos("18:15")
        )
    )
    minimo, maximo = (20, 25) if pico else (15, 20)
    return {
        "inicio": _base._fmt_min(m + minimo),
        "fim": _base._fmt_min(m + maximo),
        "pico": pico,
        "noturno": m >= _base._minutos("20:00"),
    }


_base.estimar_chegada_portao_1 = _estimar_chegada_portao_1_sem_pico_13h

for _nome in dir(_base):
    if not _nome.startswith("__"):
        globals()[_nome] = getattr(_base, _nome)

estimar_chegada_portao_1 = _estimar_chegada_portao_1_sem_pico_13h
