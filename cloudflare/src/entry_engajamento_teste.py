import json
from datetime import datetime, timedelta

import entry as _entry
from entry import *
from estado_bus import BusState as _BusStateBase
from regras import agora_local, estimar_chegada_portao_1
from volta_referencia import ultima_saida_oficial, viagem_por_referencia

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

        bruto = await self.ctx.storage.get("engajamento_teste_consulta")
        try:
            consulta = json.loads(bruto) if bruto else None
        except Exception:
            consulta = None

        def consulta_valida_ate(corte):
            if not consulta or consulta.get("chave") != chave_volta:
                return False
            if str(consulta.get("telegram_id")) != str(admin_id):
                return False
            momento = _dt(consulta.get("consultado_em"))
            return bool(
                momento
                and base_tempo <= momento <= corte
                and corte - momento <= timedelta(minutes=JANELA_CONSULTA_MIN)
            )

        avisos_volta = int(contador.get("avisos", 0))

        if (
            not fluxo.get("primeiro_encerrado")
            and avisos_volta < MAX_AVISOS_POR_VOLTA
            and primeiro_em <= agora < autor_em
        ):
            if consulta_valida_ate(corte_primeiro):
                fluxo["primeiro_enviado"] = True
                fluxo["primeiro_encerrado"] = True
                await self.ctx.storage.put("engajamento_teste_fluxo", json.dumps(fluxo, ensure_ascii=False))
                contador["avisos"] = avisos_volta + 1
                await self.ctx.storage.put("engajamento_teste_contador_volta", json.dumps(contador, ensure_ascii=False))
                return {
                    "enviar": True,
                    "telegram_id": str(admin_id),
                    "origem": "consulta_primeiro",
                    "aviso_principal": 1,
                    "avisos_na_volta": contador["avisos"],
                }
            return {"enviar": False}

        if not fluxo.get("autor_enviado") and agora >= autor_em:
            fluxo["primeiro_encerrado"] = True
            fluxo["autor_enviado"] = True
            await self.ctx.storage.put("engajamento_teste_fluxo", json.dumps(fluxo, ensure_ascii=False))
            autor = estado.get("telegram_id") if confirmacao_valida else None
            if autor is not None and str(autor) == str(admin_id):
                return {
                    "enviar": True,
                    "telegram_id": str(admin_id),
                    "origem": "autor_ultima_confirmacao",
                    "fallback": True,
                    "avisos_na_volta": avisos_volta,
                }

        if (
            not fluxo.get("segundo_enviado")
            and avisos_volta < MAX_AVISOS_POR_VOLTA
            and agora >= segundo_em
        ):
            if consulta_valida_ate(corte_segundo):
                fluxo["segundo_enviado"] = True
                await self.ctx.storage.put("engajamento_teste_fluxo", json.dumps(fluxo, ensure_ascii=False))
                contador["avisos"] = avisos_volta + 1
                await self.ctx.storage.put("engajamento_teste_contador_volta", json.dumps(contador, ensure_ascii=False))
                return {
                    "enviar": True,
                    "telegram_id": str(admin_id),
                    "origem": "consulta_segundo",
                    "aviso_principal": 2,
                    "avisos_na_volta": contador["avisos"],
                }
            return {"enviar": False}

        return {"enviar": False}


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

    async def scheduled(self, controller, env, ctx):
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
