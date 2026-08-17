import json
import random
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
TEMPO_AUTOR_NORMAL_MIN = 8
TEMPO_AUTOR_PICO_MIN = 13
ANTECEDENCIA_CORTE_MIN = 1
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
        await self.ctx.storage.put("engajamento_consultas", json.dumps(consultas[-150:], ensure_ascii=False))
        return {"ok": True, "chave": chave}

    async def _consultas_da_janela(self, chave_volta, inicio, corte, admin_id=None):
        bruto = await self.ctx.storage.get("engajamento_consultas")
        try:
            consultas = json.loads(bruto) if bruto else []
        except Exception:
            consultas = []

        ids = []
        for consulta in consultas:
            if consulta.get("chave") != chave_volta:
                continue
            momento = _dt(consulta.get("consultado_em"))
            if not momento or momento < inicio or momento > corte:
                continue
            if corte - momento > timedelta(minutes=JANELA_CONSULTA_MIN):
                continue
            telegram_id = str(consulta.get("telegram_id"))
            if admin_id is not None and telegram_id != str(admin_id):
                continue
            if telegram_id not in ids:
                ids.append(telegram_id)

        if len(ids) <= MAX_CONVIDADOS:
            return ids
        return random.sample(ids, MAX_CONVIDADOS)

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

        saida = _momento(viagem["hora"], agora)
        confirmacao = _dt(estado.get("horario"))
        confirmacao_valida = bool(confirmacao and confirmacao.date() == agora.date() and confirmacao >= saida)
        base_tempo = confirmacao if confirmacao_valida else saida
        chave_lacuna = _chave_lacuna(viagem, base_tempo)

        bruto_fluxo = await self.ctx.storage.get("engajamento_fluxo")
        try:
            fluxo = json.loads(bruto_fluxo) if bruto_fluxo else {}
        except Exception:
            fluxo = {}
        if fluxo.get("chave_lacuna") != chave_lacuna:
            fluxo = {
                "chave_lacuna": chave_lacuna,
                "primeiro_enviado": False,
                "primeiro_encerrado": False,
                "autor_enviado": False,
                "segundo_enviado": False,
            }

        pico = bool(estimar_chegada_portao_1(viagem["hora"])["pico"])
        primeiro_min = TEMPO_PICO_PRIMEIRO_MIN if pico else TEMPO_NORMAL_PRIMEIRO_MIN
        segundo_min = TEMPO_PICO_SEGUNDO_MIN if pico else TEMPO_NORMAL_SEGUNDO_MIN
        autor_min = TEMPO_AUTOR_PICO_MIN if pico else TEMPO_AUTOR_NORMAL_MIN

        primeiro_em = base_tempo + timedelta(minutes=primeiro_min)
        segundo_em = base_tempo + timedelta(minutes=segundo_min)
        autor_em = base_tempo + timedelta(minutes=autor_min)
        corte_primeiro = primeiro_em - timedelta(minutes=ANTECEDENCIA_CORTE_MIN)
        corte_segundo = segundo_em - timedelta(minutes=ANTECEDENCIA_CORTE_MIN)
        avisos_volta = int(contador.get("avisos", 0))

        # Primeiro lote: não encerra a etapa se o cron não encontrar candidato.
        # O corte continua fixo em 1 minuto antes do disparo planejado.
        if (
            not fluxo.get("primeiro_encerrado")
            and avisos_volta < MAX_AVISOS_POR_VOLTA
            and primeiro_em <= agora < autor_em
        ):
            ids = await self._consultas_da_janela(chave_volta, base_tempo, corte_primeiro, admin_id)
            if ids:
                fluxo["primeiro_enviado"] = True
                fluxo["primeiro_encerrado"] = True
                await self.ctx.storage.put("engajamento_fluxo", json.dumps(fluxo, ensure_ascii=False))
                contador["avisos"] = avisos_volta + 1
                await self.ctx.storage.put("engajamento_contador_volta", json.dumps(contador, ensure_ascii=False))
                return {
                    "enviar": True,
                    "ids": ids,
                    "pico": pico,
                    "origem": "consultas_primeiro",
                    "aviso_principal": 1,
                    "avisos_na_volta": contador["avisos"],
                    "chave_lacuna": chave_lacuna,
                }
            return {"enviar": False}

        # Fallback ao último marcador. Ao chegar aqui, o primeiro fluxo é
        # encerrado definitivamente, evitando sobreposição com o segundo.
        if not fluxo.get("autor_enviado") and agora >= autor_em:
            fluxo["primeiro_encerrado"] = True
            fluxo["autor_enviado"] = True
            await self.ctx.storage.put("engajamento_fluxo", json.dumps(fluxo, ensure_ascii=False))
            autor = estado.get("telegram_id") if confirmacao_valida else None
            autor = str(autor) if autor is not None else None
            autor_valido = bool(autor and autor != "admin" and (admin_id is None or autor == str(admin_id)))
            if autor_valido:
                return {
                    "enviar": True,
                    "ids": [autor],
                    "pico": pico,
                    "origem": "autor_ultima_confirmacao",
                    "fallback": True,
                    "avisos_na_volta": avisos_volta,
                    "chave_lacuna": chave_lacuna,
                }

        # Segundo lote: só é concluído quando houver envio real. Pode ser
        # rechecado nos crons seguintes, sempre usando o mesmo corte fixo.
        if (
            not fluxo.get("segundo_enviado")
            and avisos_volta < MAX_AVISOS_POR_VOLTA
            and agora >= segundo_em
        ):
            ids = await self._consultas_da_janela(chave_volta, base_tempo, corte_segundo, admin_id)
            if ids:
                fluxo["segundo_enviado"] = True
                await self.ctx.storage.put("engajamento_fluxo", json.dumps(fluxo, ensure_ascii=False))
                contador["avisos"] = avisos_volta + 1
                await self.ctx.storage.put("engajamento_contador_volta", json.dumps(contador, ensure_ascii=False))
                return {
                    "enviar": True,
                    "ids": ids,
                    "pico": pico,
                    "origem": "consultas_segundo",
                    "aviso_principal": 2,
                    "avisos_na_volta": contador["avisos"],
                    "chave_lacuna": chave_lacuna,
                }
            return {"enviar": False}

        return {"enviar": False}


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
