import entry_micro_flex as _entry
from entry_micro_flex import *

from dados import HORARIOS, PONTOS, ROTULOS_PONTOS
from entry_admin import _SENTIDOS_ROTULO, sentidos_disponiveis
from estado_bus import _resultado_correcao_manual
from regras import agora_local


def _minutos(hora):
    h, m = map(int, hora.split(":"))
    return h * 60 + m


def _bloco_micro_atual():
    horarios = HORARIOS.get("micro", [])
    if not horarios:
        return []
    grupos = []
    atual = [horarios[0]]
    for item in horarios[1:]:
        anterior = atual[-1]
        if _minutos(item["hora"]) - _minutos(anterior["hora"]) <= 90:
            atual.append(item)
        else:
            grupos.append(atual)
            atual = [item]
    grupos.append(atual)
    agora = agora_local()
    minuto = agora.hour * 60 + agora.minute

    def distancia(grupo):
        inicio = _minutos(grupo[0]["hora"])
        fim = _minutos(grupo[-1].get("fim", grupo[-1]["hora"]))
        if inicio <= minuto <= fim:
            return 0
        return min(abs(minuto - inicio), abs(minuto - fim))

    return min(grupos, key=distancia)


def teclado_referencias_micro():
    grupo = _bloco_micro_atual()
    botoes = [
        {"text": item["hora"], "callback_data": f"admin_micro_ref_{item['hora'].replace(':', '')}"}
        for item in grupo
    ]
    botoes.append({"text": "🔵 Esporádica", "callback_data": "admin_micro_ref_ESP"})
    linhas = [botoes[i:i + 3] for i in range(0, len(botoes), 3)]
    linhas.append([{"text": "⬅️ Voltar", "callback_data": "admin_ajuste_menu"}])
    return {"inline_keyboard": linhas}


def teclado_pontos_micro(referencia):
    botoes = []
    for ponto_id, ponto in PONTOS.items():
        if ponto_id == "garagem":
            continue
        botoes.append({
            "text": ROTULOS_PONTOS.get(ponto_id, ponto["nome"]),
            "callback_data": f"admin_micro_p_{referencia}_{ponto_id}",
        })
    linhas = [botoes[i:i + 2] for i in range(0, len(botoes), 2)]
    linhas.append([{"text": "⬅️ Escolher referência", "callback_data": "admin_micro_menu"}])
    return {"inline_keyboard": linhas}


def teclado_sentidos_micro(referencia, ponto_id):
    linhas = [
        [{
            "text": _SENTIDOS_ROTULO.get(sentido, sentido),
            "callback_data": f"admin_micro_s_{referencia}_{ponto_id}_{sentido}",
        }]
        for sentido in sentidos_disponiveis(ponto_id)
    ]
    linhas.append([{
        "text": "⬅️ Escolher outro ponto",
        "callback_data": f"admin_micro_ref_{referencia}",
    }])
    return {"inline_keyboard": linhas}


class BusState(_entry.BusState):
    async def corrigir_micro_admin(self, referencia, ponto_id, sentido):
        sentido = str(sentido or "").upper()
        resultado_rota = _resultado_correcao_manual(ponto_id, sentido)
        if resultado_rota is None:
            return {"ok": False, "motivo": "combinacao_invalida"}

        status = await self.micro_status()
        if not status.get("ativo"):
            return {"ok": False, "motivo": "micro_inativo"}

        agora = agora_local()
        estado = await self._carregar_chave_estado("estado_micro")
        anterior = estado.get("ponto_atual")
        historico = list(estado.get("historico", []))
        historico.append({
            "ponto_id": ponto_id,
            "horario": agora.isoformat(),
            "telegram_id": "admin",
            "correcao_manual": True,
            "sentido": sentido,
            "referencia_micro": referencia,
        })
        estado.update({
            "ponto_anterior": anterior,
            "ponto_atual": ponto_id,
            "horario": agora.isoformat(),
            "telegram_id": "admin",
            "resultado_rota": {**resultado_rota, "correcao_micro_admin": True},
            "historico": historico[-40:],
        })
        await self._salvar_chave_estado("estado_micro", estado)

        if referencia == "ESP":
            await self.ctx.storage.put("micro_modo", "esporadico")
            await self.ctx.storage.delete("micro_referencia_hora")
            await self.ctx.storage.delete("micro_referencia_origem")
            referencia_hora = None
            referencia_origem = None
        else:
            if len(referencia) != 4 or not referencia.isdigit():
                return {"ok": False, "motivo": "referencia_invalida"}
            hora = f"{referencia[:2]}:{referencia[2:]}"
            viagem = next((v for v in HORARIOS.get("micro", []) if v.get("hora") == hora), None)
            if viagem is None:
                return {"ok": False, "motivo": "referencia_invalida"}
            await self.ctx.storage.put("micro_modo", "referenciado")
            await self.ctx.storage.put("micro_referencia_hora", viagem["hora"])
            await self.ctx.storage.put("micro_referencia_origem", viagem.get("origem", ""))
            referencia_hora = viagem["hora"]
            referencia_origem = viagem.get("origem", "")

        return {
            "ok": True,
            "ponto": PONTOS[ponto_id]["nome"],
            "sentido": sentido,
            "modo": "esporadico" if referencia == "ESP" else "referenciado",
            "referencia_hora": referencia_hora,
            "referencia_origem": referencia_origem,
        }


class Default(_entry.Default):
    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao == "admin_micro_menu":
            if not self._telegram_admin(telegram_id):
                return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            return await enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "🚐 Correção administrativa do micro\n\nEscolha primeiro a volta de referência:",
                reply_markup=teclado_referencias_micro(),
            )

        if acao.startswith("admin_micro_ref_"):
            if not self._telegram_admin(telegram_id):
                return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            referencia = acao.replace("admin_micro_ref_", "", 1)
            if referencia != "ESP":
                hora = f"{referencia[:2]}:{referencia[2:]}" if len(referencia) == 4 and referencia.isdigit() else ""
                if not any(v.get("hora") == hora for v in HORARIOS.get("micro", [])):
                    return await enviar_mensagem(
                        self.env.TELEGRAM_BOT_TOKEN,
                        chat_id,
                        "⚠️ Referência inválida.",
                        reply_markup=teclado_referencias_micro(),
                    )
            rotulo = "Operação esporádica" if referencia == "ESP" else f"Volta {referencia[:2]}:{referencia[2:]}"
            return await enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                f"🧭 {rotulo}\n\nAgora escolha o ponto do micro:",
                reply_markup=teclado_pontos_micro(referencia),
            )

        if acao.startswith("admin_micro_p_"):
            if not self._telegram_admin(telegram_id):
                return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            bruto = acao.replace("admin_micro_p_", "", 1)
            try:
                referencia, ponto_id = bruto.split("_", 1)
            except ValueError:
                referencia, ponto_id = "", ""
            if ponto_id not in PONTOS or ponto_id == "garagem":
                return await enviar_mensagem(
                    self.env.TELEGRAM_BOT_TOKEN,
                    chat_id,
                    "⚠️ Ponto inválido.",
                    reply_markup=teclado_referencias_micro(),
                )
            return await enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                f"📍 {ROTULOS_PONTOS.get(ponto_id, PONTOS[ponto_id]['nome'])}\n\nEscolha o sentido do micro:",
                reply_markup=teclado_sentidos_micro(referencia, ponto_id),
            )

        if acao.startswith("admin_micro_s_"):
            if not self._telegram_admin(telegram_id):
                return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            bruto = acao.replace("admin_micro_s_", "", 1)
            partes = bruto.rsplit("_", 1)
            if len(partes) != 2:
                return await enviar_mensagem(self.env.TELEGRAM_BOT_TOKEN, chat_id, "⚠️ Correção inválida.")
            prefixo, sentido = partes
            try:
                referencia, ponto_id = prefixo.split("_", 1)
            except ValueError:
                referencia, ponto_id = "", ""

            resultado = await self._estado().corrigir_micro_admin(referencia, ponto_id, sentido)
            if not resultado.get("ok"):
                texto = (
                    "🚫 O micro precisa estar marcado como em operação antes da correção."
                    if resultado.get("motivo") == "micro_inativo"
                    else "⚠️ Não consegui aplicar a correção do micro."
                )
                return await enviar_mensagem(
                    self.env.TELEGRAM_BOT_TOKEN,
                    chat_id,
                    texto,
                    reply_markup=teclado_referencias_micro(),
                )

            referencia_txt = (
                "🔵 Operação esporádica"
                if resultado.get("modo") == "esporadico"
                else f"🧭 Volta: {resultado['referencia_hora']} — {resultado.get('referencia_origem', '')}"
            )
            texto = (
                "✅ Micro corrigido manualmente.\n\n"
                + referencia_txt
                + f"\n📍 {resultado['ponto']}\n"
                + _SENTIDOS_ROTULO.get(resultado["sentido"], resultado["sentido"])
            )
            return await enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                texto,
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "⬅️ Ajuste manual", "callback_data": "admin_ajuste_menu"}],
                        [{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}],
                    ]
                },
            )

        return await super()._acao(acao, chat_id, telegram_id)
