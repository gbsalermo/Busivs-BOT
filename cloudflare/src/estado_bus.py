import json
from workers import DurableObject
from regras import estado_vazio, montar_localizacao, registrar_passagem


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
        estado, texto = montar_localizacao(estado)
        await self._salvar(estado)
        return {"texto": texto}

    async def registrar(self, ponto_id, telegram_id=None):
        estado = await self._carregar()
        estado, resultado = registrar_passagem(estado, ponto_id, telegram_id)
        await self._salvar(estado)
        return resultado

    async def limpar(self):
        await self._salvar(estado_vazio())
        return {"ok": True}
