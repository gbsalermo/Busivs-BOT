from datetime import datetime

from dados import BLOCOS_PRINCIPAL, HORARIOS, ROTA

MARCADOR_FIM_BLOCO = "operacao_encerrada_bloco"
MARCADOR_RETORNO_GARAGEM = "retorno_garagem"
PONTOS_RETORNO_GARAGEM = {"fitotecnia", "solos_neas_florestal", "garagem"}
MARCADOR_AUTORIZACAO_RETORNO = "_autorizar_retorno_garagem"


def _parse_datetime(valor):
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor
    try:
        return datetime.fromisoformat(valor)
    except (TypeError, ValueError):
        return None


def _ocorrencias(ponto_id):
    return [i for i, item in enumerate(ROTA) if item["ponto_id"] == ponto_id]


def _indice_atual_linear(estado):
    resultado = (estado or {}).get("resultado_rota") or {}
    indice = resultado.get("indice_atual")
    if indice is not None:
        return indice

    ponto_atual = (estado or {}).get("ponto_atual")
    ocorrencias = _ocorrencias(ponto_atual) if ponto_atual else []
    if len(ocorrencias) == 1:
        return ocorrencias[0]

    return None


def _ordem_linear_valida(estado, novo_ponto):
    """Valida apenas a ordem estrutural dentro da volta atual."""
    ponto_atual = (estado or {}).get("ponto_atual")
    if not ponto_atual or ponto_atual == novo_ponto:
        return True

    indice_atual = _indice_atual_linear(estado)
    if indice_atual is None:
        return True

    destinos = _ocorrencias(novo_ponto)
    if not destinos:
        return True

    return any(indice > indice_atual for indice in destinos)


def _momento_saida(hora, agora):
    hh, mm = map(int, hora.split(":"))
    return agora.replace(hour=hh, minute=mm, second=0, microsecond=0)


def _bloco_ultima_volta_atual(agora):
    candidatos = []
    for indice, bloco in enumerate(BLOCOS_PRINCIPAL):
        ultima = _momento_saida(bloco["ultima"], agora)
        if agora < ultima:
            continue
        if indice + 1 < len(BLOCOS_PRINCIPAL):
            proximo = _momento_saida(BLOCOS_PRINCIPAL[indice + 1]["inicio"], agora)
            if agora >= proximo:
                continue
        candidatos.append((ultima, bloco))
    return max(candidatos, key=lambda item: item[0]) if candidatos else (None, None)


def _retorno_garagem_liberado(estado, agora):
    resultado = (estado or {}).get("resultado_rota") or {}
    ultima_dt, bloco = _bloco_ultima_volta_atual(agora)
    if bloco is None:
        return False

    if resultado.get(MARCADOR_RETORNO_GARAGEM) and resultado.get("bloco_id") == bloco["id"]:
        return True

    confirmado_em = _parse_datetime((estado or {}).get("horario"))
    if confirmado_em is None or confirmado_em < ultima_dt:
        return False

    indice_atual = _indice_atual_linear(estado)
    indice_portao_1 = next(
        (i for i, item in enumerate(ROTA) if item["ponto_id"] == "portao_1"),
        None,
    )
    return indice_atual is not None and indice_portao_1 is not None and indice_atual >= indice_portao_1


def _houve_nova_saida_desde_confirmacao(estado, agora):
    confirmado_em = _parse_datetime((estado or {}).get("horario"))
    if confirmado_em is None or confirmado_em.date() != agora.date():
        return False

    for viagem in HORARIOS.get("principal", []):
        saida = _momento_saida(viagem["hora"], agora)
        if confirmado_em < saida <= agora:
            return True

    return False


def validar_deslocamento(
    estado,
    novo_ponto,
    agora,
    permitir_ciclo=True,
    exigir_nova_saida_para_ciclo=False,
):
    """Valida somente ordem da rota, ciclo e encerramento de bloco.

    Não existe bloqueio por tempo de deslocamento entre pontos.
    """
    resultado_rota = (estado or {}).get("resultado_rota") or {}
    if resultado_rota.get(MARCADOR_FIM_BLOCO):
        return {
            "aceito": False,
            "motivo": "fora_circulacao",
            "origem": "Garagem",
            "proxima": resultado_rota.get("proxima"),
            "fim_previsto": resultado_rota.get("fim_previsto"),
        }

    retorno_garagem = exigir_nova_saida_para_ciclo and _retorno_garagem_liberado(estado, agora)
    if novo_ponto == "garagem" and not retorno_garagem:
        return {
            "aceito": False,
            "motivo": "ordem_rota_invalida",
            "ponto_anterior": (estado or {}).get("ponto_atual"),
            "ponto_novo": novo_ponto,
        }

    if retorno_garagem and novo_ponto in PONTOS_RETORNO_GARAGEM:
        estado[MARCADOR_AUTORIZACAO_RETORNO] = True
        return None

    ordem_valida = _ordem_linear_valida(estado, novo_ponto)
    if not ordem_valida:
        if not permitir_ciclo:
            return {
                "aceito": False,
                "motivo": "ordem_rota_invalida",
                "ponto_anterior": (estado or {}).get("ponto_atual"),
                "ponto_novo": novo_ponto,
            }

        if exigir_nova_saida_para_ciclo and not _houve_nova_saida_desde_confirmacao(estado, agora):
            return {
                "aceito": False,
                "motivo": "ordem_rota_invalida",
                "ponto_anterior": (estado or {}).get("ponto_atual"),
                "ponto_novo": novo_ponto,
                "sem_nova_saida": True,
            }

    return None
