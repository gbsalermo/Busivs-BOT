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
    """Menor quantidade plausível de trechos entre dois pontos.

    A rota começa e termina no RU. Para permitir uma volta seguinte, tratamos
    a sequência como cíclica, mas não contamos duas vezes o RU duplicado nas
    extremidades.
    """
    origens = _ocorrencias(origem)
    destinos = _ocorrencias(destino)
    if not origens or not destinos:
        return None

    # O último item repete o primeiro (RU), então existem len(ROTA)-1 trechos
    # efetivos em um ciclo completo.
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


def validar_deslocamento(estado, novo_ponto, agora):
    """Valida deslocamentos absurdos e janelas já encerradas.

    Retorna ``None`` quando não há motivo para bloquear. Quando o salto é longo
    demais para o tempo decorrido, ou quando o bloco operacional já terminou,
    retorna um resultado compatível com o fluxo de rejeição de
    ``registrar_passagem``.
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
