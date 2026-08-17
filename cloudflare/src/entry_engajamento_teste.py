import json
from datetime import datetime, timedelta

import entry as _entry
from entry import *
from estado_bus import BusState as _BusStateBase
from regras import agora_local, estimar_chegada_portao_1
from volta_referencia import ultima_saida_oficial, viagem_por_referencia

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
    async def registrar_consulta_engajamento_teste(self, telegram_id, admin_id):
        if telegram_id is None or str(telegram_id) != str(admin_id):
            return {"ok": False, "motivo": "nao_admin"}
        agora = agora_local()
        status = await self.status_registro_principal()
        if not status.get("ativo"):
            return {"ok": False, "motivo": "fora_operacao"}
        estado = await self._carregar()
        viagem = viagem_por_referencia(estado) or ultima_saida_oficial(agora)
        chave = _chave_volta(viagem, agora)
        if not chave:
            return {"ok": False, "motivo": "sem_volta"}
        consulta = {
            "chave": chave,
            "telegram_id": str(telegram_id),
            "consultado_em": agora.isoformat(),
        }
        await self.ctx.storage.put("engajamento_teste_consulta", json.dumps(consulta, ensure_ascii=False))
        return {"ok": True, "chave": chave}

    async def candidato_engajamento_teste(self, admin_id):
        agora = agora_local()
        status = await self.status_registro_principal()
        if not status.get("ativo"):
            return {"enviar": False}

        estado = await self._carregar()
        viagem = viagem_por_referencia(estado) or ultima_saida_oficial(agora)
        if not viagem:
            return {"enviar": False}
        chave = _chave_volta(viagem, agora)
        if str(await self.ctx.storage.get("engajamento_teste_disparado")) == chave:
            return {"enviar": False}

        saida = _momento(viagem["hora"], agora)
        confirmacao = _dt(estado.get("horario"))
        base_tempo = max(saida, confirmacao) if confirmacao and confirmacao.date() == agora.date() else saida
        pico = bool(estimar_chegada_portao_1(viagem["hora"])["pico"])
        limite = TEMPO_PICO_MIN if pico else TEMPO_NORMAL_MIN
        if agora < base_tempo + timedelta(minutes=limite):
            return {"enviar": False}

        ultimo_autor = estado.get("telegram_id")
        if confirmacao and ultimo_autor is not None and str(ultimo_autor) == str(admin_id):
            await self.ctx.storage.put("engajamento_teste_disparado", chave)
            return {"enviar": True, "telegram_id": str(admin_id), "pico": pico, "limite": limite, "chave": chave, "origem": "ultima_confirmacao"}

        bruto = await self.ctx.storage.get("engajamento_teste_consulta")
        try:
            consulta = json.loads(bruto) if bruto else None
        except Exception:
            consulta = None
        if not consulta or consulta.get("chave") != chave:
            return {"enviar": False}
        if str(consulta.get("telegram_id")) != str(admin_id):
            return {"enviar": False}

        consultado_em = _dt(consulta.get("consultado_em"))
        inicio_consultas = confirmacao if confirmacao and confirmacao.date() == agora.date() else saida
        if not consultado_em or consultado_em < inicio_consultas:
            return {"enviar": False}
        if agora - consultado_em > timedelta(minutes=JANELA_CONSULTA_MIN):
            return {"enviar": False}

        await self.ctx.storage.put("engajamento_teste_disparado", chave)
        return {"enviar": True, "telegram_id": str(admin_id), "pico": pico, "limite": limite, "chave": chave, "origem": "consulta"}


class Default(_entry.Default):
    async def _onde(self, chat_id, telegram_id=None):
        if telegram_id is not None and self._telegram_admin(telegram_id):
            await self._estado().registrar_consulta_engajamento_teste(
                telegram_id,
                str(self.env.ADMIN_TELEGRAM_ID).strip(),
            )
        return await super()._onde(chat_id, telegram_id)

    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao == "engajamento_nao_vi":
            return await _entry._core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "👍 Tudo bem. Obrigado por responder!",
                reply_markup=_entry.teclado_localizacao(self._telegram_admin(telegram_id)),
            )
        return await super()._acao(acao, chat_id, telegram_id)

    async def scheduled(self, controller):
        admin_id = str(self.env.ADMIN_TELEGRAM_ID).strip()
        candidato = await self._estado().candidato_engajamento_teste(admin_id)
        if not candidato.get("enviar"):
            return
        await _entry._core.enviar_mensagem(
            self.env.TELEGRAM_BOT_TOKEN,
            admin_id,
            "🧪 TESTE DE COLABORAÇÃO\n\n"
            "🚌 Você viu o circular recentemente?\n\n"
            "A localização está há alguns minutos sem nova confirmação. "
            "Se você viu o ônibus passar, ajude atualizando o ponto.",
            reply_markup=teclado_convite(),
        )
