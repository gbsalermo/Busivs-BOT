import json
from workers import DurableObject
from biblioteca_contexto import ajustar_primeira_biblioteca, montar_localizacao_com_biblioteca
from ciclo_noturno import reiniciar_se_novo_ciclo_noturno
from expiracao_volta import expirar_confirmacao_volta_anterior
from horarios_pico import montar_resumo_horarios
from regras import agora_local, estado_vazio, registrar_passagem
from validacao_rota import validar_deslocamento


class BusState(DurableObject):
    async def _carregar(self):
        bruto = await self.ctx.storage.get("estado")
        if not bruto:
            return estado_vazio()
        try:
            return json.loads(bruto)
        except Exception:
            return estado_vazio()

    async def _salvar(self, estado):
        await self.ctx.storage.put("estado", json.dumps(estado, ensure_ascii=False))

    async def localizacao(self):
        estado = await self._carregar()
        agora = agora_local()
        estado = reiniciar_se_novo_ciclo_noturno(estado, agora)
        estado = expirar_confirmacao_volta_anterior(estado, agora)
        estado, texto = montar_localizacao_com_biblioteca(estado, agora)
        await self._salvar(estado)
        return {"texto": texto}

    async def resumo_horarios(self):
        estado = await self._carregar()
        agora = agora_local()
        estado = reiniciar_se_novo_ciclo_noturno(estado, agora)
        estado = expirar_confirmacao_volta_anterior(estado, agora)
        await self._salvar(estado)
        return {"texto": montar_resumo_horarios(estado=estado, agora=agora)}

    async def registrar(self, ponto_id, telegram_id=None):
        estado = await self._carregar()
        agora = agora_local()
        estado_original = estado
        estado = reiniciar_se_novo_ciclo_noturno(estado, agora)
        estado = expirar_confirmacao_volta_anterior(estado, agora)

        if estado != estado_original:
            await self._salvar(estado)

        bloqueio = validar_deslocamento(estado, ponto_id, agora)
        if bloqueio is not None:
            return bloqueio

        estado, resultado = registrar_passagem(
            estado,
            ponto_id,
            telegram_id,
            agora=agora,
        )
        estado = ajustar_primeira_biblioteca(estado, resultado, agora)
        await self._salvar(estado)
        return resultado

    async def limpar(self):
        await self._salvar(estado_vazio())
        return {"ok": True}
