import entry_antiteleporte as _entry
from entry_antiteleporte import *
import entry_admin_hub as _hub
import entry_core as _core


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
