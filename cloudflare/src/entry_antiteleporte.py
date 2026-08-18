from datetime import datetime

import entry_admin_hub as _entry
from entry_admin_hub import *
from dados import ROTA
from regras import agora_local


# Mínimos físicos conservadores. Servem apenas para barrar saltos impossíveis,
# não para estimar o tempo real da viagem.
MINIMOS_ESPECIAIS = {
    ("portao_1", "biblioteca"): 3,
    ("portao_1", "torre_cotec"): 5,
    ("portao_1", "ru"): 8,
    ("ponto_externo_2", "portao_1"): 2,
    ("ponto_externo_2", "biblioteca"): 5,
    ("ponto_externo_2", "ru"): 10,
    ("ponto_externo_1", "ru"): 12,
    ("portao_2", "ru"): 14,
    ("biblioteca", "ru"): 4,
}


def _indice_futuro(estado, ponto_id):
    resultado = (estado or {}).get("resultado_rota") or {}
    atual = resultado.get("indice_atual")
    if atual is None:
        return None
    candidatos = [i for i, item in enumerate(ROTA) if i > atual and item.get("ponto_id") == ponto_id]
    return min(candidatos) if candidatos else None


def _minimo_generico(estado, ponto_id):
    resultado = (estado or {}).get("resultado_rota") or {}
    atual = resultado.get("indice_atual")
    destino = _indice_futuro(estado, ponto_id)
    if atual is None or destino is None:
        return None
    saltos = destino - atual
    if saltos <= 1:
        return 1
    # Conservador: evita teletransporte sem bloquear ônibus adiantado/rápido.
    return 1 + (saltos - 1) * 2


def _validar_tempo_minimo(estado, ponto_id, agora):
    anterior = (estado or {}).get("ponto_atual")
    horario = (estado or {}).get("horario")
    if not anterior or not horario or anterior == ponto_id:
        return None
    try:
        confirmado_em = datetime.fromisoformat(str(horario))
    except Exception:
        return None
    if confirmado_em.date() != agora.date() or agora < confirmado_em:
        return None

    minimo = MINIMOS_ESPECIAIS.get((anterior, ponto_id))
    if minimo is None:
        minimo = _minimo_generico(estado, ponto_id)
    if minimo is None:
        return None

    decorrido = (agora - confirmado_em).total_seconds() / 60
    if decorrido + 0.05 < minimo:
        return {
            "aceito": False,
            "motivo": "deslocamento_impossivel_tempo",
            "ponto_anterior": anterior,
            "ponto_novo": ponto_id,
            "minimo_minutos": minimo,
            "decorrido_minutos": max(0, int(decorrido)),
        }
    return None


class BusState(_entry.BusState):
    async def registrar(self, ponto_id, telegram_id=None):
        estado = await self._carregar()
        bloqueio = _validar_tempo_minimo(estado, ponto_id, agora_local())
        if bloqueio:
            return bloqueio
        return await super().registrar(ponto_id, telegram_id)


class Default(_entry.Default):
    pass
