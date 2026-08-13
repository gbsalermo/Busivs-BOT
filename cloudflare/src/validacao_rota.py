from datetime import datetime

from dados import ROTA

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


def _ordem_linear_valida(estado, novo_ponto):
    """Valida avanço sem permitir wrap automático para uma nova volta.

    Usado no micro, cuja confirmação deve respeitar a ordem da volta atual.
    O RU final continua sendo aceito após Torre/COTEC, mas um ponto anterior
    como Pavilhão II não pode aparecer depois de um ponto do fim da rota.
    """
    resultado = (estado or {}).get("resultado_rota") or {}
    indice_atual = resultado.get("indice_atual")
    ponto_atual = (estado or {}).get("ponto_atual")

    if indice_atual is None or not ponto_atual or ponto_atual == novo_ponto:
        return True

    destinos = _ocorrencias(novo_ponto)
    if not destinos:
        return True

    return any(indice > indice_atual for indice in destinos)


def validar_deslocamento(estado, novo_ponto, agora, permitir_ciclo=True):
    """Valida deslocamentos absurdos e janelas já encerradas.

    ``permitir_ciclo=False`` torna a validação estrita para uma única volta,
    impedindo que um ponto anterior seja interpretado automaticamente como
    início de outro ciclo.
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

    if not permitir_ciclo and not _ordem_linear_valida(estado, novo_ponto):
        return {
            "aceito": False,
            "motivo": "ordem_rota_invalida",
            "ponto_anterior": (estado or {}).get("ponto_atual"),
            "ponto_novo": novo_ponto,
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
