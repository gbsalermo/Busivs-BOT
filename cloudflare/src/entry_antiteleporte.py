from datetime import datetime, timedelta
import json

import entry_admin_hub as _entry
from entry_admin_hub import *
from dados import ROTA
from regras import agora_local, estado_vazio


# Proteção mínima contra saltos fisicamente impossíveis:
# - 30 segundos por ponto obrigatório avançado;
# - pontos opcionais não aumentam o mínimo;
# - Portão 1 -> Biblioteca mantém mínimo especial de 60 segundos;
# - sem confirmação anterior, qualquer ponto pode ser a primeira evidência;
# - se a mesma pessoa repetir o mesmo ponto após um bloqueio, a reafirmação passa.
JANELA_REAFIRMACAO_MINUTOS = 2
CHAVE_TENTATIVA = "antiteleporte_tentativa"
SEGUNDOS_POR_PONTO = 30
MINIMO_PORTAO1_BIBLIOTECA_SEGUNDOS = 60

SEQUENCIA_SAIDA_GARAGEM = [
    "ru",
    "fitotecnia",
    "solos_neas_florestal",
    "pavilhao_1",
    "biblioteca",
    "pavilhao_2",
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
    candidatos = [i for i, item in enumerate(ROTA) if i > indice_atual and item.get("ponto_id") == ponto_id]
    return min(candidatos) if candidatos else None


def _pontos_obrigatorios_entre(indice_atual, indice_destino):
    if indice_destino <= indice_atual:
        return None
    obrigatorios = 0
    for i in range(indice_atual + 1, indice_destino + 1):
        item = ROTA[i]
        if item.get("opcional", False):
            continue
        obrigatorios += 1
    return obrigatorios


def _minimo_segundos_da_rota(estado, ponto_id):
    anterior = (estado or {}).get("ponto_atual")
    if anterior == "portao_1" and ponto_id == "biblioteca":
        return MINIMO_PORTAO1_BIBLIOTECA_SEGUNDOS

    if anterior == "garagem":
        if ponto_id == "ru":
            return 0
        try:
            indice = SEQUENCIA_SAIDA_GARAGEM.index(ponto_id)
        except ValueError:
            return None
        return max(1, indice) * SEGUNDOS_POR_PONTO

    atual = _indice_atual(estado)
    if atual is None:
        return None
    destino = _indice_destino_futuro(atual, ponto_id)
    if destino is None:
        return None
    pontos = _pontos_obrigatorios_entre(atual, destino)
    return pontos * SEGUNDOS_POR_PONTO if pontos is not None else None


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

    async def _registrar_reafirmacao(self, estado, ponto_id, telegram_id):
        """Segunda tentativa consciente também pode corrigir uma sequência antiga.

        Quando o primeiro clique foi bloqueado apenas porque o estado salvo aponta
        para outra parte da rota, a repetição do MESMO usuário no MESMO ponto
        passa a valer como nova evidência e reinicia a posição colaborativa.
        Isso evita deixar o ônibus preso em uma sequência antiga em horários de
        voltas muito próximas, sem liberar um clique isolado potencialmente errado.
        """
        await self._salvar_tentativa_antiteleporte(None)
        await self._salvar(estado_vazio())
        return await super().registrar(ponto_id, telegram_id)

    async def registrar(self, ponto_id, telegram_id=None):
        estado = await self._carregar()
        agora = agora_local()
        anterior = (estado or {}).get("ponto_atual")
        horario = _parse_horario((estado or {}).get("horario"))

        reafirmando = await self._reafirmacao_valida(estado, ponto_id, telegram_id, agora)
        if reafirmando:
            tentativa = await self._carregar_tentativa_antiteleporte()
            if tentativa and tentativa.get("motivo") == "ordem_rota_invalida":
                return await self._registrar_reafirmacao(estado, ponto_id, telegram_id)
            await self._salvar_tentativa_antiteleporte(None)
            return await super().registrar(ponto_id, telegram_id)

        if not anterior or not horario or anterior == ponto_id:
            await self._salvar_tentativa_antiteleporte(None)
            return await super().registrar(ponto_id, telegram_id)

        if horario.date() != agora.date() or agora < horario:
            await self._salvar_tentativa_antiteleporte(None)
            return await super().registrar(ponto_id, telegram_id)

        minimo_segundos = _minimo_segundos_da_rota(estado, ponto_id)
        if minimo_segundos is not None:
            decorrido_segundos = max(0.0, (agora - horario).total_seconds())
            if decorrido_segundos + 3 < minimo_segundos:
                await self._salvar_tentativa_antiteleporte({
                    "telegram_id": str(telegram_id) if telegram_id is not None else None,
                    "ponto_id": ponto_id,
                    "ponto_anterior": anterior,
                    "horario": agora.isoformat(),
                    "motivo": "deslocamento_impossivel_tempo",
                })
                return {
                    "aceito": False,
                    "motivo": "deslocamento_impossivel_tempo",
                    "ponto_anterior": anterior,
                    "ponto_novo": ponto_id,
                    "minimo_segundos": minimo_segundos,
                    "decorrido_segundos": int(decorrido_segundos),
                    "pode_reafirmar": telegram_id is not None,
                }

        resultado = await super().registrar(ponto_id, telegram_id)
        if not resultado.get("aceito") and resultado.get("motivo") == "ordem_rota_invalida" and telegram_id is not None:
            await self._salvar_tentativa_antiteleporte({
                "telegram_id": str(telegram_id),
                "ponto_id": ponto_id,
                "ponto_anterior": anterior,
                "horario": agora.isoformat(),
                "motivo": "ordem_rota_invalida",
            })
            return resultado

        await self._salvar_tentativa_antiteleporte(None)
        return resultado


class Default(_entry.Default):
    pass
