import json
from datetime import datetime, timedelta

import entry_admin as _entry
from entry_admin import *
from estado_bus import BusState as _BusStateBase
from regras import agora_local, estimar_chegada_portao_1
from volta_referencia import ultima_saida_oficial, viagem_por_referencia

MAX_CONVIDADOS = 3
TEMPO_NORMAL_MIN = 5
TEMPO_PICO_MIN = 10
JANELA_CONSULTA_MIN = 15


def teclado_convite():
    return {"inline_keyboard": [
        [{"text": "📍 Sim, marcar ponto", "callback_data": "local"}],
        [{"text": "❌ Não vi", "callback_data": "engajamento_nao_vi"}],
    ]}


def _momento(hora, referencia):
    h, m = map(int, hora.split(":"))
    return referencia.replace(hour=h, minute=m, second=0, microsecond=0)


def _chave_volta(viagem, agora):
    return f"{agora.date().isoformat()}|{viagem['hora']}" if viagem else None


def _dt(valor):
    try:
        return datetime.fromisoformat(str(valor)) if valor else None
    except (TypeError, ValueError):
        return None


class BusState(_BusStateBase):
    async def registrar_consulta_engajamento(self, telegram_id):
        if telegram_id is None:
            return {"ok": False}
        agora = agora_local()
        status = await self.status_registro_principal()
        if not status.get("ativo"):
            return {"ok": False, "motivo": "fora_operacao"}
        estado = await self._carregar()
        viagem = viagem_por_referencia(estado) or ultima_saida_oficial(agora)
        chave = _chave_volta(viagem, agora)
        if not chave:
            return {"ok": False, "motivo": "sem_volta"}
        bruto = await self.ctx.storage.get("engajamento_consultas")
        try:
            consultas = json.loads(bruto) if bruto else []
        except Exception:
            consultas = []
        consultas = [c for c in consultas if c.get("chave") == chave]
        consultas = [c for c in consultas if str(c.get("telegram_id")) != str(telegram_id)]
        consultas.append({"chave": chave, "telegram_id": str(telegram_id), "consultado_em": agora.isoformat()})
        await self.ctx.storage.put("engajamento_consultas", json.dumps(consultas[-50:], ensure_ascii=False))
        return {"ok": True, "chave": chave}

    async def candidatos_engajamento(self, admin_id=None):
        agora = agora_local()
        status = await self.status_registro_principal()
        if not status.get("ativo"):
            return {"enviar": False}

        estado = await self._carregar()
        viagem = viagem_por_referencia(estado) or ultima_saida_oficial(agora)
        if not viagem:
            return {"enviar": False}
        chave = _chave_volta(viagem, agora)
        if str(await self.ctx.storage.get("engajamento_disparado")) == chave:
            return {"enviar": False}

        saida = _momento(viagem["hora"], agora)
        confirmacao = _dt(estado.get("horario"))
        base_tempo = max(saida, confirmacao) if confirmacao and confirmacao.date() == agora.date() else saida
        pico = bool(estimar_chegada_portao_1(viagem["hora"])["pico"])
        limite = TEMPO_PICO_MIN if pico else TEMPO_NORMAL_MIN
        if agora < base_tempo + timedelta(minutes=limite):
            return {"enviar": False}

        bruto = await self.ctx.storage.get("engajamento_consultas")
        try:
            consultas = json.loads(bruto) if bruto else []
        except Exception:
            consultas = []
        inicio_consultas = confirmacao if confirmacao and confirmacao.date() == agora.date() else saida
        recentes = []
        for consulta in consultas:
            if consulta.get("chave") != chave:
                continue
            momento = _dt(consulta.get("consultado_em"))
            if not momento or momento < inicio_consultas or agora - momento > timedelta(minutes=JANELA_CONSULTA_MIN):
                continue
            if admin_id is not None and str(consulta.get("telegram_id")) != str(admin_id):
                continue
            recentes.append((momento, str(consulta.get("telegram_id"))))
        if not recentes:
            return {"enviar": False}

        recentes.sort(reverse=True)
        ids = []
        for _, telegram_id in recentes:
            if telegram_id not in ids:
                ids.append(telegram_id)
            if len(ids) >= MAX_CONVIDADOS:
                break
        await self.ctx.storage.put("engajamento_disparado", chave)
        return {"enviar": True, "ids": ids, "pico": pico, "limite": limite, "chave": chave}


class Default(_entry.Default):
    async def _onde(self, chat_id, telegram_id=None):
        if telegram_id is not None and not self._telegram_admin(telegram_id):
            await self._estado().registrar_consulta_engajamento(telegram_id)
        return await super()._onde(chat_id, telegram_id)

    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao == "engajamento_nao_vi":
            return await _entry._core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "👍 Tudo bem. Obrigado por responder!",
                reply_markup=_entry.teclado_localizacao_admin(self._telegram_admin(telegram_id)),
            )
        return await super()._acao(acao, chat_id, telegram_id)

    async def scheduled(self, controller):
        candidatos = await self._estado().candidatos_engajamento()
        if not candidatos.get("enviar"):
            return
        texto = (
            "🚌 Você viu o circular recentemente?\n\n"
            "A localização está há alguns minutos sem nova confirmação. "
            "Se você viu o ônibus passar, ajude atualizando o ponto."
        )
        for telegram_id in candidatos.get("ids", []):
            await _entry._core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                telegram_id,
                texto,
                reply_markup=teclado_convite(),
            )
