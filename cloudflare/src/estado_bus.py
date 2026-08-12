import json
from datetime import datetime

from workers import DurableObject

from avisos_blocos import expiracao_bloco_aviso
from regras import agora_local, estado_vazio, montar_localizacao, registrar_passagem
from validacao_rota import validar_deslocamento

MAX_AVISOS_ATIVOS = 3
MAX_TAMANHO_AVISO = 280


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
        await self._expirar_avisos_se_necessario()
        bruto = await self.ctx.storage.get("avisos")
        if not bruto:
            return []
        try:
            avisos = json.loads(bruto)
            return avisos if isinstance(avisos, list) else []
        except Exception:
            return []

    async def _salvar_avisos(self, avisos):
        await self.ctx.storage.put(
            "avisos",
            json.dumps(list(avisos)[:MAX_AVISOS_ATIVOS], ensure_ascii=False),
        )

    async def _expirar_avisos_se_necessario(self):
        expira_em = await self.ctx.storage.get("avisos_expiram_em")
        if not expira_em:
            return
        try:
            expira_em = datetime.fromisoformat(str(expira_em))
        except Exception:
            await self._limpar_avisos_interno()
            return

        if agora_local() >= expira_em:
            await self._limpar_avisos_interno()

    async def _limpar_avisos_interno(self):
        await self._salvar_avisos([])
        await self.ctx.storage.delete("avisos_expiram_em")
        await self.ctx.storage.delete("aguardando_aviso_personalizado")

    async def listar_avisos(self):
        avisos = await self._carregar_avisos()
        return {
            "avisos": avisos,
            "quantidade": len(avisos),
            "limite": MAX_AVISOS_ATIVOS,
            "expiram_em": await self.ctx.storage.get("avisos_expiram_em"),
        }

    async def adicionar_aviso(self, texto):
        texto = (texto or "").strip()
        if not texto:
            return {"ok": False, "motivo": "aviso_vazio", "avisos": await self._carregar_avisos()}
        if len(texto) > MAX_TAMANHO_AVISO:
            return {"ok": False, "motivo": "aviso_muito_longo", "avisos": await self._carregar_avisos()}

        avisos = await self._carregar_avisos()
        if texto in avisos:
            return {"ok": True, "avisos": avisos, "duplicado": True}
        if len(avisos) >= MAX_AVISOS_ATIVOS:
            return {"ok": False, "motivo": "limite_atingido", "avisos": avisos}

        agora = agora_local()
        avisos.append(texto)
        await self._salvar_avisos(avisos)
        expira_em = await self.ctx.storage.get("avisos_expiram_em")
        if not expira_em:
            expira_em = expiracao_bloco_aviso(agora).isoformat()
            await self.ctx.storage.put("avisos_expiram_em", expira_em)
        return {"ok": True, "avisos": avisos, "duplicado": False, "expiram_em": expira_em}

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
        if not avisos:
            await self.ctx.storage.delete("avisos_expiram_em")
        return {"ok": True, "removido": removido, "avisos": avisos}

    async def limpar_avisos(self):
        await self._limpar_avisos_interno()
        return {"ok": True, "avisos": []}

    async def iniciar_aviso_personalizado(self):
        await self._expirar_avisos_se_necessario()
        await self.ctx.storage.put("aguardando_aviso_personalizado", True)
        return {"ok": True}

    async def cancelar_aviso_personalizado(self):
        await self.ctx.storage.delete("aguardando_aviso_personalizado")
        return {"ok": True}

    async def aguardando_aviso_personalizado(self):
        await self._expirar_avisos_se_necessario()
        ativo = await self.ctx.storage.get("aguardando_aviso_personalizado")
        return {"ativo": bool(ativo)}

    async def salvar_aviso_personalizado(self, texto):
        resultado = await self.adicionar_aviso(texto)
        if resultado.get("ok"):
            await self.ctx.storage.delete("aguardando_aviso_personalizado")
        return resultado

    async def localizacao(self):
        estado = await self._carregar()
        estado, texto = montar_localizacao(estado)
        await self._salvar(estado)
        return {"texto": texto}

    async def registrar(self, ponto_id, telegram_id=None):
        estado = await self._carregar()
        agora = agora_local()
        avisos = await self._carregar_avisos()

        bloqueio = validar_deslocamento(estado, ponto_id, agora, avisos=avisos)
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
