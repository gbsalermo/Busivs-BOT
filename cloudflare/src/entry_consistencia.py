import entry_antiteleporte as _entry
from entry_antiteleporte import *
import entry_admin_hub as _hub
import entry_core as _core
from dados import HORARIOS, PONTOS
from regras import agora_local


def _resumo_micro_estado(status):
    linhas = ["🚐 <b>Micro — reforço</b>", "✅ Operação informada pela comunidade."]
    modo = status.get("modo")
    referencia = status.get("referencia_hora")
    origem = status.get("referencia_origem") or "RU/Residências"

    if modo == "referenciado" and referencia:
        linhas += [
            "",
            "🔵 <b>Volta de referência atual</b>",
            f"🕐 <b>{referencia}</b> — {origem}",
            "ℹ️ A referência muda quando os pontos indicam uma nova volta, não apenas pelo relógio.",
        ]
    elif modo == "esporadico":
        linhas += [
            "",
            "🔵 <b>Operação esporádica</b>",
            "Sem vínculo obrigatório com uma volta oficial.",
        ]
    else:
        linhas += [
            "",
            "⚪ Operação ativa sem referência oficial definida.",
        ]
    return "\n".join(linhas)


def _proxima_micro_mesmo_bloco(hora_atual):
    horarios = HORARIOS.get("micro", [])
    indice = next((i for i, item in enumerate(horarios) if item.get("hora") == hora_atual), None)
    if indice is None or indice + 1 >= len(horarios):
        return None
    atual = horarios[indice]
    proxima = horarios[indice + 1]
    ha = int(atual["hora"][:2]) * 60 + int(atual["hora"][3:5])
    hp = int(proxima["hora"][:2]) * 60 + int(proxima["hora"][3:5])
    return proxima if hp - ha <= 90 else None


def _resultado_retorno_garagem_micro(ponto_id):
    if ponto_id == "fitotecnia":
        proximo = {
            "id": "solos_neas_florestal",
            "nome": PONTOS["solos_neas_florestal"]["nome"],
            "opcional": False,
        }
    elif ponto_id == "solos_neas_florestal":
        proximo = {"id": "garagem", "nome": "Garagem", "opcional": False}
    else:
        return None
    return {
        "ponto_atual_id": ponto_id,
        "ponto_atual": PONTOS[ponto_id]["nome"],
        "sentido": "GARAGEM",
        "retorno_garagem": True,
        "proximo": proximo,
    }


class BusState(_entry.BusState):
    async def registrar_micro(self, ponto_id, telegram_id=None):
        estado = await self._carregar_chave_estado("estado_micro")
        if estado.get("confirmacao_nao_confiavel"):
            return await super().registrar_micro(ponto_id, telegram_id)

        status = await self.micro_status()
        referencia = status.get("referencia_hora")
        modo = status.get("modo")
        resultado_atual = estado.get("resultado_rota") or {}

        ultima_referencia_bloco = bool(
            modo == "referenciado"
            and referencia
            and _proxima_micro_mesmo_bloco(referencia) is None
        )

        retorno_iniciado = (
            ultima_referencia_bloco
            and estado.get("ponto_atual") == "ru"
            and ponto_id in {"fitotecnia", "solos_neas_florestal"}
        )
        retorno_continua = (
            resultado_atual.get("sentido") == "GARAGEM"
            and ponto_id == "solos_neas_florestal"
        )

        if retorno_iniciado or retorno_continua:
            resultado_rota = _resultado_retorno_garagem_micro(ponto_id)
            if resultado_rota is not None:
                agora = agora_local()
                historico = list(estado.get("historico", []))
                historico.append({
                    "ponto_id": ponto_id,
                    "horario": agora.isoformat(),
                    "telegram_id": telegram_id,
                })
                estado.update({
                    "ponto_anterior": estado.get("ponto_atual"),
                    "ponto_atual": ponto_id,
                    "horario": agora.isoformat(),
                    "telegram_id": telegram_id,
                    "resultado_rota": resultado_rota,
                    "historico": historico[-40:],
                })
                await self._salvar_chave_estado("estado_micro", estado)
                return {
                    "aceito": True,
                    "ponto": PONTOS[ponto_id]["nome"],
                    "resultado_rota": resultado_rota,
                    "retorno_garagem": True,
                }

        return await super().registrar_micro(ponto_id, telegram_id)


class Default(_entry.Default):
    async def _onde(self, chat_id, telegram_id=None):
        principal = await self._estado().localizacao()
        texto_principal = _hub._enxugar_texto_usuario(principal["texto"])
        texto = "🚌 <b>CIRCULAR PRINCIPAL</b>\n\n" + texto_principal

        avisos = await self._avisos_ativos()
        impacto = _core.impacto_localizacao(avisos)
        if impacto:
            texto += "\n\n" + impacto

        status = await self._status_micro()
        if status.get("ativo"):
            micro = await self._estado().localizacao_micro()
            texto_micro = _hub._enxugar_texto_usuario(micro.get("texto") or "")
            texto += "\n\n────────────\n\n🚐 <b>MICRO — REFORÇO</b>\n\n" + texto_micro

        return await _core.enviar_mensagem(
            self.env.TELEGRAM_BOT_TOKEN,
            chat_id,
            texto,
            parse_mode="HTML",
            reply_markup=_hub.teclado_localizacao_limpo(self._telegram_admin(telegram_id)),
        )

    async def _horarios(self, chat_id):
        dados = await self._estado().resumo_horarios()
        texto = _hub._enxugar_texto_usuario(dados["texto"])
        status = await self._status_micro()
        if status.get("ativo"):
            texto = _core.limitar_resumo_principal(texto, 2) + "\n\n" + _resumo_micro_estado(status)

        return await _core.enviar_mensagem(
            self.env.TELEGRAM_BOT_TOKEN,
            chat_id,
            _hub._enxugar_texto_usuario(texto),
            parse_mode="HTML",
            reply_markup=_core.teclado_voltar(),
        )

    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao == "onde":
            return await self._onde(chat_id, telegram_id)
        if acao == "horarios":
            return await self._horarios(chat_id)
        return await super()._acao(acao, chat_id, telegram_id)
