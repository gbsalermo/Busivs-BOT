import json
from datetime import datetime, timedelta

import entry_admin as _entry
from entry_admin import *
from estado_bus import BusState as _BusStateBase
from regras import agora_local, estimar_chegada_portao_1
from volta_referencia import ultima_saida_oficial, viagem_por_referencia

MAX_CONVIDADOS = 10
MAX_AVISOS_POR_VOLTA = 2
TEMPO_NORMAL_PRIMEIRO_MIN = 5
TEMPO_NORMAL_SEGUNDO_MIN = 15
TEMPO_PICO_PRIMEIRO_MIN = 10
TEMPO_PICO_SEGUNDO_MIN = 20
JANELA_CONSULTA_MIN = 30


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


def _chave_lacuna(viagem, base_tempo):
    return f"{viagem['hora']}|{base_tempo.isoformat()}"


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
        await self.ctx.storage.put("engajamento_consultas", json.dumps(consultas[-100:], ensure_ascii=False))
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

        chave_volta = _chave_volta(viagem, agora)

        bruto_contador = await self.ctx.storage.get("engajamento_contador_volta")
        try:
            contador = json.loads(bruto_contador) if bruto_contador else {}
        except Exception:
            contador = {}
        if contador.get("chave_volta") != chave_volta:
            contador = {"chave_volta": chave_volta, "avisos": 0}
        if int(contador.get("avisos", 0)) >= MAX_AVISOS_POR_VOLTA:
            return {"enviar": False}

        saida = _momento(viagem["hora"], agora)
        confirmacao = _dt(estado.get("horario"))
        confirmacao_valida = bool(confirmacao and confirmacao.date() == agora.date() and confirmacao >= saida)
        base_tempo = confirmacao if confirmacao_valida else saida
        chave_lacuna = _chave_lacuna(viagem, base_tempo)

        bruto_estagio = await self.ctx.storage.get("engajamento_estagio")
        try:
            controle = json.loads(bruto_estagio) if bruto_estagio else {}
        except Exception:
            controle = {}
        if controle.get("chave_lacuna") != chave_lacuna:
            controle = {"chave_lacuna": chave_lacuna, "estagio": 0}

        pico = bool(estimar_chegada_portao_1(viagem["hora"])["pico"])
        primeiro = TEMPO_PICO_PRIMEIRO_MIN if pico else TEMPO_NORMAL_PRIMEIRO_MIN
        segundo = TEMPO_PICO_SEGUNDO_MIN if pico else TEMPO_NORMAL_SEGUNDO_MIN
        decorrido = agora - base_tempo

        estagio_atual = int(controle.get("estagio", 0))
        if estagio_atual < 1 and decorrido >= timedelta(minutes=primeiro):
            proximo_estagio = 1
        elif estagio_atual < 2 and decorrido >= timedelta(minutes=segundo):
            proximo_estagio = 2
        else:
            return {"enviar": False}

        bruto = await self.ctx.storage.get("engajamento_consultas")
        try:
            consultas = json.loads(bruto) if bruto else []
        except Exception:
            consultas = []

        recentes = []
        for consulta in consultas:
            if consulta.get("chave") != chave_volta:
                continue
            momento = _dt(consulta.get("consultado_em"))
            if not momento or momento < base_tempo or agora - momento > timedelta(minutes=JANELA_CONSULTA_MIN):
                continue
            telegram_id = str(consulta.get("telegram_id"))
            if admin_id is not None and telegram_id != str(admin_id):
                continue
            recentes.append((momento, telegram_id))

        ids = []
        ultimo_autor = estado.get("telegram_id")
        if confirmacao_valida and ultimo_autor is not None:
            ultimo_autor = str(ultimo_autor)
            if ultimo_autor != "admin" and (admin_id is None or ultimo_autor == str(admin_id)):
                ids.append(ultimo_autor)

        recentes.sort(reverse=True)
        for _, telegram_id in recentes:
            if telegram_id not in ids:
                ids.append(telegram_id)
            if len(ids) >= MAX_CONVIDADOS:
                break
        if not ids:
            return {"enviar": False}

        await self.ctx.storage.put(
            "engajamento_estagio",
            json.dumps({"chave_lacuna": chave_lacuna, "estagio": proximo_estagio}, ensure_ascii=False),
        )
        contador["avisos"] = int(contador.get("avisos", 0)) + 1
        await self.ctx.storage.put("engajamento_contador_volta", json.dumps(contador, ensure_ascii=False))

        return {
            "enviar": True,
            "ids": ids[:MAX_CONVIDADOS],
            "pico": pico,
            "estagio": proximo_estagio,
            "limite": primeiro if proximo_estagio == 1 else segundo,
            "chave_lacuna": chave_lacuna,
            "avisos_na_volta": contador["avisos"],
        }


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
