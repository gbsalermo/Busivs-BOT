import regras_core as _core

HORARIOS_NOTURNOS_RAPIDOS = {"20:40", "21:40", "22:30"}


def _estimar_chegada_portao_1_noturno_rapido(hora_saida):
    if hora_saida not in HORARIOS_NOTURNOS_RAPIDOS:
        return _core._estimar_chegada_portao_1_sem_pico_13h(hora_saida)
    m = _core._base._minutos(hora_saida)
    return {"inicio": _core._base._fmt_min(m + 10), "fim": _core._base._fmt_min(m + 15), "pico": False, "noturno": True}


def _viagem_em_retorno_noturno_rapido(agora=None):
    agora = agora or _core._base.agora_local()
    ma = agora.hour * 60 + agora.minute
    hs = _core._base.HORARIOS["principal"]
    for i, h in enumerate(hs):
        previsao = _estimar_chegada_portao_1_noturno_rapido(h["hora"])
        margem = 0 if h["hora"] in HORARIOS_NOTURNOS_RAPIDOS else _core._base.MARGEM_RETORNO_MINUTOS
        inicio = _core._base._minutos(previsao["fim"]) + margem
        proxima = _core._base._minutos(hs[i + 1]["hora"]) if i + 1 < len(hs) else 1440
        fim = min(inicio + _core._base.DURACAO_RETORNO_MINUTOS, proxima)
        if inicio <= ma < fim:
            return {"viagem": h, "origem": _core._base._nome_origem(h["origem"]), "inicio_retorno": _core._base._fmt_min(inicio), "fim_retorno": _core._base._fmt_min(fim), "proxima": hs[i + 1] if i + 1 < len(hs) else None}
    return None


_core._base.estimar_chegada_portao_1 = _estimar_chegada_portao_1_noturno_rapido
_core._base.viagem_em_retorno = _viagem_em_retorno_noturno_rapido
_core.estimar_chegada_portao_1 = _estimar_chegada_portao_1_noturno_rapido
_core.viagem_em_retorno = _viagem_em_retorno_noturno_rapido
for _nome in dir(_core):
    if not _nome.startswith("__"):
        globals()[_nome] = getattr(_core, _nome)
estimar_chegada_portao_1 = _estimar_chegada_portao_1_noturno_rapido
viagem_em_retorno = _viagem_em_retorno_noturno_rapido
