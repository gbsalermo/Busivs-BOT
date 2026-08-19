from datetime import datetime, timedelta
import json

import entry_admin_hub as _entry
from entry_admin_hub import *
from dados import ROTA
from regras import agora_local


# Regra temporária e flexível:
# - 30 segundos mínimos por ponto/etapa avançada na rota;
# - os tempos se acumulam quando vários pontos são pulados;
# - Portão 1 -> Biblioteca mantém mínimo especial de 1 minuto;
# - sem confirmação anterior, qualquer ponto pode ser a primeira evidência;
# - se a mesma pessoa repetir o mesmo ponto após um bloqueio, a reafirmação passa.
SEGUNDOS_POR_PONTO = 30
JANELA_REAFIRMACAO_MINUTOS = 2
CHAVE_TENTATIVA = "antiteleporte_tentativa"


# Garagem não faz parte da ROTA colaborativa, então usamos a sequência física
# de saída até o Portão 1. RU pode ser a primeira confirmação imediatamente.
SEQUENCIA_SAIDA_GARAGEM = [
    "ru",
    "fitotecnia",
    "solos_neas_florestal",
    "pavilhao_1",
    "biblioteca",
    "pavilhao_2",
    "pavilhao_engenharia",
    "portao_2",
    "ponto_externo_1",
    "ponto_externo_2",
    "portao_1",
]


def _indice_atual(estado):
    resultado = (estado or {}).get("resultado_rota") or {}
    indice = resultado.get("indice_atual")
    if indice is not None:
        return indice

    atual = (estado or {}).get("ponto_atual")
    ocorrencias = [i for i, item in enumerate(ROTA) if item.get("ponto_id") == atual]
    return ocorrencias[0] if len(ocorrencias) == 1 else None


def _indice_destino_futuro(indice_atual, ponto_id):
    candidatos = [
        i for i, item in enumerate(ROTA)
        if i > indice_atual and item.get("ponto_id") == ponto_id
    ]
    return min(candidatos) if candidatos else None


def _etapas_entre(indice_atual, indice_destino):
    """Conta cada etapa/ponto avançado na rota, inclusive pontos opcionais.

    A trava é propositalmente leve: cada etapa soma apenas 30 segundos.
    Assim, pular quatro etapas exige 2 minutos; se houver uma confirmação
    intermediária, a contagem recomeça a partir dela.
    """
    if indice_destino <= indice_atual:
        return None
    return indice_destino - indice_atual


def _minimo_segundos_da_rota(estado, ponto_id):
    anterior = (estado or {}).get("ponto_atual")

    # Esse trecho é fisicamente mais longo que os demais e mantém 1 minuto.
    if anterior == "portao_1" and ponto_id == "biblioteca":
        return 60

    if anterior == "garagem":
        if ponto_id == "ru":
            return 0
        try:
            indice = SEQUENCIA_SAIDA_GARAGEM.index(ponto_id)
        except ValueError:
            return None
        return max(SEGUNDOS_POR_PONTO, indice * SEGUNDOS_POR_PONTO)

    atual = _indice_atual(estado)
    if atual is None:
        return None

    destino = _indice_destino_futuro(atual, ponto_id)
    if destino is None:
        return None

    etapas = _etapas_entre(atual, destino)
    if etapas is None:
        return None
    return etapas * SEGUNDOS_POR_PONTO


def _parse_horario(valor):
    try:
        return datetime.fromisoformat(str(valor)) if valor else None
    except Exception:
        return None


class BusState(_entry.BusState):
    async def _carregar_tentativa_antiteleporte(self):
        bruto = await self.ctx.storage.get(CHAVE_TENTATIVA)
        if not bruto:
            return None
        try:
            return json.loads(bruto)
        except Exception:
            return None

    async def _salvar_tentativa_antiteleporte(self, tentativa):
        if tentativa is None:
            await self.ctx.storage.delete(CHAVE_TENTATIVA)
            return
        await self.ctx.storage.put(CHAVE_TENTATIVA, json.dumps(tentativa, ensure_ascii=False))

    async def _reafirmacao_valida(self, estado, ponto_id, telegram_id, agora):
        if telegram_id is None:
            return False
        tentativa = await self._carregar_tentativa_antiteleporte()
        if not tentativa:
            return False

        if str(tentativa.get("telegram_id")) != str(telegram_id):
            return False
        if tentativa.get("ponto_id") != ponto_id:
            return False
        if tentativa.get("ponto_anterior") != (estado or {}).get("ponto_atual"):
            return False

        momento = _parse_horario(tentativa.get("horario"))
        if momento is None:
            return False
        delta = agora - momento
        return timedelta(0) <= delta <= timedelta(minutes=JANELA_REAFIRMACAO_MINUTOS)

    async def registrar(self, ponto_id, telegram_id=None):
        estado = await self._carregar()
        agora = agora_local()
        anterior = (estado or {}).get("ponto_atual")
        horario = _parse_horario((estado or {}).get("horario"))

        # Sem ponto anterior, qualquer ponto pode ser a primeira evidência real.
        if not anterior or not horario or anterior == ponto_id:
            await self._salvar_tentativa_antiteleporte(None)
            return await super().registrar(ponto_id, telegram_id)

        # A segunda tentativa da mesma pessoa para o mesmo salto funciona como
        # reafirmação consciente e passa pela trava temporal.
        if await self._reafirmacao_valida(estado, ponto_id, telegram_id, agora):
            await self._salvar_tentativa_antiteleporte(None)
            return await super().registrar(ponto_id, telegram_id)

        if horario.date() != agora.date() or agora < horario:
            await self._salvar_tentativa_antiteleporte(None)
            return await super().registrar(ponto_id, telegram_id)

        minimo_segundos = _minimo_segundos_da_rota(estado, ponto_id)
        if minimo_segundos is None:
            # A validação estrutural existente continua responsável por ordem
            # inválida, mudança de volta e demais casos especiais.
            await self._salvar_tentativa_antiteleporte(None)
            return await super().registrar(ponto_id, telegram_id)

        decorrido_segundos = max(0, (agora - horario).total_seconds())
        if decorrido_segundos + 3 < minimo_segundos:
            await self._salvar_tentativa_antiteleporte({
                "telegram_id": str(telegram_id) if telegram_id is not None else None,
                "ponto_id": ponto_id,
                "ponto_anterior": anterior,
                "horario": agora.isoformat(),
            })
            return {
                "aceito": False,
                "motivo": "deslocamento_impossivel_tempo",
                "ponto_anterior": anterior,
                "ponto_novo": ponto_id,
                "minimo_segundos": minimo_segundos,
                "minimo_minutos": minimo_segundos / 60,
                "decorrido_segundos": int(decorrido_segundos),
                "decorrido_minutos": int(decorrido_segundos // 60),
                "pode_reafirmar": telegram_id is not None,
            }

        await self._salvar_tentativa_antiteleporte(None)
        return await super().registrar(ponto_id, telegram_id)


class Default(_entry.Default):
    pass
