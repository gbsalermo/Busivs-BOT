import json
from workers import DurableObject
from regras import agora_local, estado_vazio, montar_localizacao, registrar_passagem
from validacao_rota import validar_deslocamento

MAX_AVISOS_ATIVOS = 3


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

    async def _carregar_avisos(self):
        bruto = await self.ctx.storage.get("avisos")
        if not bruto:
            return []
        try:
            avisos = json.loads(bruto)
            return avisos if isinstance(avisos, list) else []
        except Exception:
            return []

    async def _salvar_avisos(self, avisos):
        avisos = list(avisos)[-MAX_AVISOS_ATIVOS:]
        await self.ctx.storage.put("avisos", json.dumps(avisos, ensure_ascii=False))

    async def listar_avisos(self):
        return {"avisos": await self._carregar_avisos()}

    async def adicionar_aviso(self, texto):
        texto = (texto or "").strip()
        if not texto:
            return {"ok": False, "motivo": "aviso_vazio"}

        avisos = await self._carregar_avisos()
        if texto in avisos:
            return {"ok": True, "avisos": avisos, "duplicado": True}

        avisos.append(texto)
        avisos = avisos[-MAX_AVISOS_ATIVOS:]
        await self._salvar_avisos(avisos)
        return {"ok": True, "avisos": avisos, "duplicado": False}

    async def remover_aviso(self, indice):
        avisos = await self._carregar_avisos()
        try:
            indice = int(indice)
        except Exception:
            return {"ok": False, "motivo": "indice_invalido", "avisos": avisos}

        if indice < 0 or indice >= len(avisos):
            return {"ok": False, "motivo": "indice_invalido", "avisos": avisos}

        removido = avisos.pop(indice)
        await self._salvar_avisos(avisos)
        return {"ok": True, "removido": removido, "avisos": avisos}

    async def limpar_avisos(self):
        await self._salvar_avisos([])
        return {"ok": True, "avisos": []}

    async def iniciar_aviso_personalizado(self):
        await self.ctx.storage.put("aguardando_aviso_personalizado", True)
        return {"ok": True}

    async def cancelar_aviso_personalizado(self):
        await self.ctx.storage.delete("aguardando_aviso_personalizado")
        return {"ok": True}

    async def aguardando_aviso_personalizado(self):
        ativo = await self.ctx.storage.get("aguardando_aviso_personalizado")
        return {"ativo": bool(ativo)}

    async def salvar_aviso_personalizado(self, texto):
        await self.ctx.storage.delete("aguardando_aviso_personalizado")
        return await self.adicionar_aviso(texto)

    async def localizacao(self):
        estado = await self._carregar()
        estado, texto = montar_localizacao(estado)
        await self._salvar(estado)
        return {"texto": texto}

    async def registrar(self, ponto_id, telegram_id=None):
        estado = await self._carregar()
        agora = agora_local()

        bloqueio = validar_deslocamento(estado, ponto_id, agora)
        if bloqueio is not None:
            return bloqueio

        estado, resultado = registrar_passagem(
            estado,
            ponto_id,
            telegram_id,
            agora=agora,
        )
        await self._salvar(estado)
        return resultado

    async def limpar(self):
        await self._salvar(estado_vazio())
        return {"ok": True}
