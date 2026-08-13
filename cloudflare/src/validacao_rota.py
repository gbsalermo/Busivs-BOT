from datetime import datetime

from dados import BLOCOS_PRINCIPAL, HORARIOS, ROTA

# A confirmação colaborativa registra o momento do clique, não o instante exato
# em que o ônibus cruzou o ponto. Por isso esta validação é deliberadamente
# conservadora: pontos próximos nunca são bloqueados apenas por tempo.
#
# Para saltos longos, porém, exigimos uma janela mínima antes de aceitar a nova
# confirmação. Isso impede sequências como Biblioteca -> Pavilhão I -> RU em
# poucos segundos sem tornar o sistema rígido para atrasos reais.
SEGUNDOS_POR_TRECHO_LONGO = 25
DISTANCIA_LIVRE = 2
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


def _distancia_ciclica(origem, destino):
    """Menor quantidade plausível de trechos entre dois pontos."""
    origens = _ocorrencias(origem)
    destinos = _ocorrencias(destino)
    if not origens or not destinos:
        return None

    ciclo = max(1, len(ROTA) - 1)
    distancias = []

    for i_origem in origens:
        for i_destino in destinos:
            a = 0 if i_origem == len(ROTA) - 1 else i_origem
            b = 0 if i_destino == len(ROTA) - 1 else i_destino
            distancia = (b - a) % ciclo
            if distancia == 0 and origem != destino:
                distancia = ciclo
            distancias.append(distancia)

    return min(distancias) if distancias else None


def _indice_atual_linear(estado):
    resultado = (estado or {}).get("resultado_rota") or {}
    indice = resultado.get("indice_atual")
    if indice is not None:
        return indice

    # Na primeira confirmação ainda pode não existir resultado_rota. Quando o
    # ponto aparece uma única vez na rota, ele próprio define a posição atual.
    ponto_atual = (estado or {}).get("ponto_atual")
    ocorrencias = _ocorrencias(ponto_atual) if ponto_atual else []
    if len(ocorrencias) == 1:
        return ocorrencias[0]

    return None


def _ordem_linear_valida(estado, novo_ponto):
    """Valida avanço dentro da volta atual sem fazer wrap automaticamente."""
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
    """Indica se uma nova volta oficial pode justificar o reinício da rota.

    No circular principal a rota é cíclica, mas um ponto anterior só pode ser
    interpretado como pertencente à volta seguinte quando pelo menos uma nova
    saída oficial ocorreu depois da última confirmação salva.
    """
    confirmado_em = _parse_datetime((estado or {}).get("horario"))
    if confirmado_em is None:
        return False

    if confirmado_em.date() != agora.date():
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
    """Valida deslocamentos absurdos, ordem da rota e janelas encerradas.

    ``permitir_ciclo=False`` impede qualquer wrap para uma volta seguinte.

    ``exigir_nova_saida_para_ciclo=True`` mantém a flexibilidade do principal,
    mas só permite um ponto anterior da rota quando uma nova saída oficial já
    ocorreu depois da última confirmação. Assim Torre -> Pavilhão II não vira
    artificialmente uma nova volta enquanto o horário ainda pertence à mesma
    viagem; depois de uma nova saída oficial, o reinício volta a ser possível.
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

    # Na última volta do bloco, após uma confirmação no Portão 1 ou em ponto
    # posterior do retorno, Fitotecnia/Solos/Garagem formam um trecho especial
    # de encerramento. Ele não deve ser confundido com o wrap de uma nova volta.
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

    ponto_atual = estado.get("ponto_atual")
    horario_atual = _parse_datetime(estado.get("horario"))

    if not ponto_atual or not horario_atual or ponto_atual == novo_ponto:
        return None

    distancia = _distancia_ciclica(ponto_atual, novo_ponto)
    if distancia is None or distancia <= DISTANCIA_LIVRE:
        return None

    decorrido = max(0, int((agora - horario_atual).total_seconds()))
    minimo = (distancia - DISTANCIA_LIVRE) * SEGUNDOS_POR_TRECHO_LONGO

    if decorrido >= minimo:
        return None

    return {
        "aceito": False,
        "motivo": "deslocamento_improvavel",
        "ponto_anterior": ponto_atual,
        "ponto_novo": novo_ponto,
        "distancia_trechos": distancia,
        "segundos_decorridos": decorrido,
        "segundos_minimos": minimo,
    }
