from datetime import datetime

from dados import ROTA

# A confirmação colaborativa registra o momento do clique, não o instante exato
# em que o ônibus cruzou o ponto. Por isso esta validação é deliberadamente
# conservadora: pontos próximos nunca são bloqueados apenas por tempo.
SEGUNDOS_POR_TRECHO_LONGO = 25
DISTANCIA_LIVRE = 2

AVISO_PORTAO_1_FECHADO = "🚪 Portão 1 fechado"
AVISO_PORTAO_2_FECHADO = "🚪 Portão 2 fechado"


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


def _distancia_operacional(origem, destino, avisos):
    """Ajusta somente exceções de deslocamento já conhecidas.

    Portão fechado significa acesso fechado, não ponto removido. Quando o P1
    fecha, o ônibus ainda atende o P1 e pode retornar ao campus pelo P2. Assim,
    P1 -> P2 deve ser aceito como um deslocamento operacional curto, apesar de
    ser contrário à sequência da rota padrão.
    """
    avisos = set(avisos or [])

    if AVISO_PORTAO_1_FECHADO in avisos and origem == "portao_1" and destino == "portao_2":
        return 1

    return _distancia_ciclica(origem, destino)


def validar_deslocamento(estado, novo_ponto, agora, avisos=None):
    """Valida deslocamentos temporalmente absurdos considerando desvios ativos."""
    ponto_atual = estado.get("ponto_atual")
    horario_atual = _parse_datetime(estado.get("horario"))

    if not ponto_atual or not horario_atual or ponto_atual == novo_ponto:
        return None

    distancia = _distancia_operacional(ponto_atual, novo_ponto, avisos)
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
