import json
from datetime import datetime, timedelta

import entry as _entry
from entry import *
from estado_bus import BusState as _BusStateBase
from regras import agora_local, estimar_chegada_portao_1
from volta_referencia import ultima_saida_oficial, viagem_por_referencia

MAX_AVISOS_POR_VOLTA = 2
TEMPO_NORMAL_PRIMEIRO_MIN = 5
TEMPO_PICO_PRIMEIRO_MIN = 10
TEMPO_AUTOR_NORMAL_MIN = 8
TEMPO_AUTOR_PICO_MIN = 13
INTERVALO_ENTRE_AVISOS_MIN = 10
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
        consulta = {"chave": chave, "telegram_id": str(telegram_id), "consultado_em": agora.isoformat()}
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

        chave_volta = _chave_volta(viagem, agora)
        bruto_contador = await self.ctx.storage.get("engajamento_teste_contador_volta")
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

        bruto_fluxo = await self.ctx.storage.get("engajamento_teste_fluxo")
        try:
            fluxo = json.loads(bruto_fluxo) if bruto_fluxo else {}
        except Exception:
            fluxo = {}
        if fluxo.get("chave_lacuna") != chave_lacuna:
            fluxo = {"chave_lacuna": chave_lacuna, "avisos_lacuna": 0, "ultimo_aviso_em": None}

        avisos_lacuna = int(fluxo.get("avisos_lacuna", 0))
        ultimo_aviso_em = _dt(fluxo.get("ultimo_aviso_em"))
        pico = bool(estimar_chegada_portao_1(viagem["hora"])["pico"])
        primeiro = TEMPO_PICO_PRIMEIRO_MIN if pico else TEMPO_NORMAL_PRIMEIRO_MIN
        fallback_autor = TEMPO_AUTOR_PICO_MIN if pico else TEMPO_AUTOR_NORMAL_MIN

        if avisos_lacuna == 0:
            if agora < base_tempo + timedelta(minutes=primeiro):
                return {"enviar": False}
            inicio_candidatos = base_tempo
        else:
            if ultimo_aviso_em is None or agora < ultimo_aviso_em + timedelta(minutes=INTERVALO_ENTRE_AVISOS_MIN):
                return {"enviar": False}
            inicio_candidatos = ultimo_aviso_em

        origem = None
        elegivel = False
        bruto = await self.ctx.storage.get("engajamento_teste_consulta")
        try:
            consulta = json.loads(bruto) if bruto else None
        except Exception:
            consulta = None
        if consulta and consulta.get("chave") == chave_volta and str(consulta.get("telegram_id")) == str(admin_id):
            consultado_em = _dt(consulta.get("consultado_em"))
            if consultado_em and consultado_em >= inicio_candidatos and agora - consultado_em <= timedelta(minutes=JANELA_CONSULTA_MIN):
                elegivel = True
                origem = "consulta"

        if not elegivel:
            autor = estado.get("telegram_id") if confirmacao_valida else None
            autor = str(autor) if autor is not None else None
            autor_valido = bool(autor and autor == str(admin_id))
            marco_autor = base_tempo + timedelta(minutes=fallback_autor) if avisos_lacuna == 0 else ultimo_aviso_em + timedelta(minutes=INTERVALO_ENTRE_AVISOS_MIN)
            if not autor_valido or agora < marco_autor:
                return {"enviar": False}
            elegivel = True
            origem = "autor_ultima_confirmacao"

        fluxo = {
            "chave_lacuna": chave_lacuna,
            "avisos_lacuna": avisos_lacuna + 1,
            "ultimo_aviso_em": agora.isoformat(),
        }
        await self.ctx.storage.put("engajamento_teste_fluxo", json.dumps(fluxo, ensure_ascii=False))
        contador["avisos"] = int(contador.get("avisos", 0)) + 1
        await self.ctx.storage.put("engajamento_teste_contador_volta", json.dumps(contador, ensure_ascii=False))

        return {
            "enviar": True,
            "telegram_id": str(admin_id),
            "pico": pico,
            "origem": origem,
            "avisos_na_lacuna": fluxo["avisos_lacuna"],
            "avisos_na_volta": contador["avisos"],
            "chave_lacuna": chave_lacuna,
        }


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
            "A localização continua sem nova confirmação. "
            "Se você viu o ônibus passar, ajude atualizando o ponto.",
            reply_markup=teclado_convite(),
        )
