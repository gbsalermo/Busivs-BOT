import regras_base as _base
from datetime import datetime

from dados import BLOCOS_PRINCIPAL, PONTOS, ROTULOS_PONTOS

MARCADOR_FIM_BLOCO = "operacao_encerrada_bloco"
MARCADOR_RETORNO_GARAGEM = "retorno_garagem"
PONTOS_RETORNO_GARAGEM = {"fitotecnia", "solos_neas_florestal", "garagem"}
MARCADOR_AUTORIZACAO_RETORNO = "_autorizar_retorno_garagem"

PONTOS.setdefault("garagem", {"id": "garagem", "nome": "Garagem", "opcional": False})
ROTULOS_PONTOS.setdefault("garagem", "🅿️ Garagem")


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


def _momento(hora, referencia):
    hh, mm = map(int, hora.split(":"))
    return referencia.replace(hour=hh, minute=mm, second=0, microsecond=0)


def _bloco_ultima_volta_atual(agora):
    candidatos = []
    for indice, bloco in enumerate(BLOCOS_PRINCIPAL):
        ultima_dt = _momento(bloco["ultima"], agora)
        if agora < ultima_dt:
            continue
        proximo_inicio = None
        if indice + 1 < len(BLOCOS_PRINCIPAL):
            proximo_inicio = _momento(BLOCOS_PRINCIPAL[indice + 1]["inicio"], agora)
            if agora >= proximo_inicio:
                continue
        candidatos.append({**bloco, "ultima_dt": ultima_dt, "proximo_inicio_dt": proximo_inicio})
    return max(candidatos, key=lambda item: item["ultima_dt"]) if candidatos else None


def _resultado_retorno_garagem(bloco, ponto_id):
    if ponto_id == "fitotecnia":
        proximo = {"id": "solos_neas_florestal", "nome": PONTOS["solos_neas_florestal"]["nome"], "opcional": False}
    elif ponto_id == "solos_neas_florestal":
        proximo = {"id": "garagem", "nome": "Garagem", "opcional": False}
    else:
        proximo = None
    return {
        MARCADOR_RETORNO_GARAGEM: True,
        "bloco_id": bloco["id"],
        "ultima_volta": bloco["ultima"],
        "ponto_atual_id": ponto_id,
        "ponto_atual": PONTOS[ponto_id]["nome"],
        "sentido": "GARAGEM",
        "proximo": proximo,
    }


def _registrar_retorno_garagem(estado, ponto_id, telegram_id, agora, bloco):
    anterior = (estado or {}).get("ponto_atual")
    historico = list((estado or {}).get("historico", []))
    registro = {"ponto_id": ponto_id, "horario": agora.isoformat(), "telegram_id": telegram_id}
    historico = (historico + [registro])[-_base.MAX_HISTORICO_REGISTROS:]
    if ponto_id == "garagem":
        resultado_rota = {
            MARCADOR_FIM_BLOCO: True,
            "garagem_confirmada": True,
            "bloco_id": bloco["id"],
            "inicio_bloco": bloco["inicio"],
            "ultima_volta": bloco["ultima"],
            "fim_previsto": agora.isoformat(),
            "fim_do_dia": bloco.get("proximo_inicio_dt") is None,
            "proxima": None,
        }
        novo = {
            "ponto_anterior": anterior,
            "ponto_atual": "garagem",
            "horario": agora.isoformat(),
            "telegram_id": telegram_id,
            "resultado_rota": resultado_rota,
            "historico": historico,
        }
        return novo, {"aceito": True, "ponto": "Garagem", "resultado_rota": resultado_rota, "bloco_encerrado": True, "garagem_confirmada": True}
    resultado_rota = _resultado_retorno_garagem(bloco, ponto_id)
    novo = {
        "ponto_anterior": anterior,
        "ponto_atual": ponto_id,
        "horario": agora.isoformat(),
        "telegram_id": telegram_id,
        "resultado_rota": resultado_rota,
        "historico": historico,
    }
    return novo, {"aceito": True, "primeiro_registro": anterior is None, "ponto": PONTOS[ponto_id]["nome"], "resultado_rota": resultado_rota, "retorno_garagem": True}


_base.estimar_chegada_portao_1 = _estimar_chegada_portao_1_sem_pico_13h

for _nome in dir(_base):
    if not _nome.startswith("__"):
        globals()[_nome] = getattr(_base, _nome)

estimar_chegada_portao_1 = _estimar_chegada_portao_1_sem_pico_13h
_registrar_passagem_base = _base.registrar_passagem


def registrar_passagem(estado, ponto_id, telegram_id=None, agora=None):
    agora = agora or _base.agora_local()
    autorizado = bool((estado or {}).get(MARCADOR_AUTORIZACAO_RETORNO))
    if ponto_id == "garagem" and not autorizado:
        return estado, {"aceito": False, "motivo": "ordem_rota_invalida", "ponto_novo": ponto_id}
    if ponto_id in PONTOS_RETORNO_GARAGEM and autorizado:
        bloco = _bloco_ultima_volta_atual(agora)
        if bloco is None:
            return estado, {"aceito": False, "motivo": "fora_circulacao"}
        return _registrar_retorno_garagem(estado, ponto_id, telegram_id, agora, bloco)
    return _registrar_passagem_base(estado, ponto_id, telegram_id, agora)
