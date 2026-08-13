import json
from datetime import datetime

from workers import DurableObject

from avisos_blocos import expiracao_bloco_aviso
from biblioteca_contexto import ajustar_primeiro_ponto, montar_localizacao_com_biblioteca
from ciclo_noturno import reiniciar_se_novo_ciclo_noturno
from expiracao_volta import expirar_confirmacao_volta_anterior
from horarios_pico import montar_resumo_horarios
from micro import janela_operacao_micro_atual, micro_pode_operar_agora
from regras import agora_local, estado_vazio, registrar_passagem
from transicao_bloco import confirmacao_inicia_novo_bloco
from validacao_rota import validar_deslocamento

MAX_AVISOS_ATIVOS = 3
MAX_TAMANHO_AVISO = 280


class BusState(DurableObject):
    async def _carregar_chave_estado(self, chave):
        bruto = await self.ctx.storage.get(chave)
        if not bruto:
            return estado_vazio()
        try:
            return json.loads(bruto)
        except Exception:
            return estado_vazio()

    async def _salvar_chave_estado(self, chave, estado):
        await self.ctx.storage.put(chave, json.dumps(estado, ensure_ascii=False))

    async def _carregar(self):
        return await self._carregar_chave_estado("estado")

    async def _salvar(self, estado):
        await self._salvar_chave_estado("estado", estado)

    # -------------------- AVISOS --------------------
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
        await self.ctx.storage.put("avisos", json.dumps(list(avisos)[:MAX_AVISOS_ATIVOS], ensure_ascii=False))

    async def _limpar_avisos_interno(self):
        await self._salvar_avisos([])
        await self.ctx.storage.delete("avisos_expiram_em")
        await self.ctx.storage.delete("aguardando_aviso_personalizado")

    async def _expirar_avisos_se_necessario(self):
        expira_em = await self.ctx.storage.get("avisos_expiram_em")
        if not expira_em:
            return
        try:
            limite = datetime.fromisoformat(str(expira_em))
        except Exception:
            await self._limpar_avisos_interno()
            return
        if agora_local() >= limite:
            await self._limpar_avisos_interno()

    async def listar_avisos(self):
        avisos = await self._carregar_avisos()
        return {"avisos": avisos, "quantidade": len(avisos), "limite": MAX_AVISOS_ATIVOS, "expiram_em": await self.ctx.storage.get("avisos_expiram_em")}

    async def adicionar_aviso(self, texto):
        texto = (texto or "").strip()
        avisos = await self._carregar_avisos()
        if not texto:
            return {"ok": False, "motivo": "aviso_vazio", "avisos": avisos}
        if len(texto) > MAX_TAMANHO_AVISO:
            return {"ok": False, "motivo": "aviso_muito_longo", "avisos": avisos}
        if texto in avisos:
            return {"ok": True, "duplicado": True, "avisos": avisos}
        if len(avisos) >= MAX_AVISOS_ATIVOS:
            return {"ok": False, "motivo": "limite_atingido", "avisos": avisos}
        avisos.append(texto)
        await self._salvar_avisos(avisos)
        expira_em = await self.ctx.storage.get("avisos_expiram_em")
        if not expira_em:
            expira_em = expiracao_bloco_aviso(agora_local()).isoformat()
            await self.ctx.storage.put("avisos_expiram_em", expira_em)
        return {"ok": True, "duplicado": False, "avisos": avisos, "expiram_em": expira_em}

    async def remover_aviso(self, indice):
        avisos = await self._carregar_avisos()
        try:
            indice = int(indice)
        except Exception:
            return {"ok": False, "avisos": avisos}
        if indice < 0 or indice >= len(avisos):
            return {"ok": False, "avisos": avisos}
        removido = avisos.pop(indice)
        await self._salvar_avisos(avisos)
        if not avisos:
            await self.ctx.storage.delete("avisos_expiram_em")
        return {"ok": True, "removido": removido, "avisos": avisos}

    async def limpar_avisos(self):
        await self._limpar_avisos_interno()
        return {"ok": True, "avisos": []}

    async def iniciar_aviso_personalizado(self):
        await self.ctx.storage.put("aguardando_aviso_personalizado", True)
        return {"ok": True}

    async def cancelar_aviso_personalizado(self):
        await self.ctx.storage.delete("aguardando_aviso_personalizado")
        return {"ok": True}

    async def aguardando_aviso_personalizado(self):
        await self._expirar_avisos_se_necessario()
        return {"ativo": bool(await self.ctx.storage.get("aguardando_aviso_personalizado"))}

    async def salvar_aviso_personalizado(self, texto):
        resultado = await self.adicionar_aviso(texto)
        if resultado.get("ok"):
            await self.ctx.storage.delete("aguardando_aviso_personalizado")
        return resultado

    # -------------------- MICRO --------------------
    async def _expirar_micro_se_necessario(self):
        if not await self.ctx.storage.get("micro_ativo"):
            return

        agora = agora_local()
        if not micro_pode_operar_agora(agora):
            await self.desativar_micro()
            return

        expira_em = await self.ctx.storage.get("micro_expira_em")
        if not expira_em:
            return
        try:
            limite = datetime.fromisoformat(str(expira_em))
        except Exception:
            await self.desativar_micro()
            return
        if agora >= limite:
            await self.desativar_micro()

    async def micro_status(self):
        await self._expirar_micro_se_necessario()
        return {
            "ativo": bool(await self.ctx.storage.get("micro_ativo")),
            "ativado_em": await self.ctx.storage.get("micro_ativado_em"),
            "expira_em": await self.ctx.storage.get("micro_expira_em"),
        }

    async def ativar_micro(self):
        await self._expirar_micro_se_necessario()
        if await self.ctx.storage.get("micro_ativo"):
            return {"ok": True, "ja_ativo": True, **(await self.micro_status())}

        agora = agora_local()
        janela = janela_operacao_micro_atual(agora)
        if janela is None:
            return {"ok": False, "ja_ativo": False, "motivo": "fora_horario_micro"}

        await self.ctx.storage.put("micro_ativo", True)
        await self.ctx.storage.put("micro_ativado_em", agora.isoformat())
        await self.ctx.storage.put("micro_expira_em", janela["fim"].isoformat())
        await self.ctx.storage.delete("estado_micro")
        return {"ok": True, "ja_ativo": False, **(await self.micro_status())}

    async def desativar_micro(self):
        await self.ctx.storage.delete("micro_ativo")
        await self.ctx.storage.delete("micro_ativado_em")
        await self.ctx.storage.delete("micro_expira_em")
        await self.ctx.storage.delete("estado_micro")
        return {"ok": True}

    async def localizacao_micro(self):
        await self._expirar_micro_se_necessario()
        estado = await self._carregar_chave_estado("estado_micro")
        if not await self.ctx.storage.get("micro_ativo"):
            return {"ativo": False, "estado": estado, "texto": ""}
        agora = agora_local()
        estado, texto = montar_localizacao_com_biblioteca(estado, agora)
        await self._salvar_chave_estado("estado_micro", estado)
        return {"ativo": True, "estado": estado, "texto": texto}

    async def registrar_micro(self, ponto_id, telegram_id=None):
        await self._expirar_micro_se_necessario()
        if not await self.ctx.storage.get("micro_ativo"):
            return {"aceito": False, "motivo": "micro_inativo"}
        estado = await self._carregar_chave_estado("estado_micro")
        agora = agora_local()
        bloqueio = validar_deslocamento(estado, ponto_id, agora, permitir_ciclo=False)
        if bloqueio is not None:
            return bloqueio
        estado, resultado = registrar_passagem(estado, ponto_id, telegram_id, agora=agora)
        estado = ajustar_primeiro_ponto(estado, resultado, agora)
        await self._salvar_chave_estado("estado_micro", estado)
        return resultado

    # -------------------- PRINCIPAL --------------------
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

        # Se um bloco novo já começou e o ponto informado é compatível com ele,
        # o estado anterior é abandonado por completo. Assim histórico, sentido e
        # próximo ponto do bloco antigo não contaminam a nova operação.
        if confirmacao_inicia_novo_bloco(estado, ponto_id, agora):
            estado = estado_vazio()

        if estado != estado_original:
            await self._salvar(estado)

        bloqueio = validar_deslocamento(
            estado,
            ponto_id,
            agora,
            exigir_nova_saida_para_ciclo=True,
        )
        if bloqueio is not None:
            return bloqueio

        estado, resultado = registrar_passagem(estado, ponto_id, telegram_id, agora=agora)
        estado = ajustar_primeiro_ponto(estado, resultado, agora)
        await self._salvar(estado)
        return resultado

    async def limpar(self):
        await self._salvar(estado_vazio())
        return {"ok": True}
