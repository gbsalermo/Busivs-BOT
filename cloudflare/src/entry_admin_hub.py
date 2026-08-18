import entry as _base_entry
import entry_core as _core
import entry_micro_admin as _entry
from entry_micro_admin import *


_teclado_localizacao_original = _base_entry.teclado_localizacao


def teclado_menu_ajuste_manual(micro_ativo=False, admin=False, principal_ativo=True):
    teclado = _core.teclado_menu(micro_ativo, admin, principal_ativo)
    if not admin:
        return teclado
    linhas = list(teclado.get("inline_keyboard", []))
    botao = [{"text": "🛠️ Ajuste manual", "callback_data": "admin_ajuste_menu"}]
    indice_ajuda = next(
        (i for i, linha in enumerate(linhas) if any(b.get("callback_data") == "ajuda" for b in linha)),
        len(linhas),
    )
    linhas.insert(indice_ajuda, botao)
    return {"inline_keyboard": linhas}


def teclado_localizacao_limpo(admin=False):
    return _teclado_localizacao_original(False)


def teclado_ajuste_manual():
    return {
        "inline_keyboard": [
            [{"text": "🧭 Escolher volta de referência", "callback_data": "admin_ref_menu"}],
            [{"text": "🛠️ Corrigir ponto / sentido", "callback_data": "admin_corrigir_menu"}],
            [{"text": "🚐 Corrigir micro", "callback_data": "admin_micro_menu"}],
            [{"text": "🅿️ Garagem / Encerrar bloco", "callback_data": "admin_ref_garagem"}],
            [{"text": "⬅️ Voltar ao menu", "callback_data": "menu"}],
        ]
    }


def _enxugar_texto_usuario(texto):
    if not texto:
        return texto

    substituicoes = {
        "ℹ️ Essa transição é estimada; uma nova confirmação tem prioridade.": "🕐 Estimativa pelo horário.",
        "ℹ️ Situação estimada pelo horário, não por confirmação de passagem.": "🕐 Estimativa pelo horário.",
        "ℹ️ Situação estimada pelo horário, sem confirmação recente de passagem.": "🕐 Estimativa pelo horário.",
        "ℹ️ Situação estimada pela rotina oficial; não há localização colaborativa ativa neste período.": "🕐 Estimativa pelo horário.",
        "  ℹ️ Situação baseada no horário oficial; uma confirmação de ponto tem prioridade.": "  🕐 Estimativa pelo horário.",
        "📍 Uma nova confirmação em outro ponto definirá o sentido com prioridade sobre a estimativa.": "🕐 O sentido ainda não foi confirmado.",
    }
    for antigo, novo in substituicoes.items():
        texto = texto.replace(antigo, novo)

    remover_prefixos = (
        "📌 Esta referência está ",
        "ℹ️ Ela permanece enquanto ainda for operacionalmente plausível.",
        "⏳ Referência atual válida, no máximo, até ",
        "🕐 A referência anterior atingiu o limite operacional de ",
        "🕐 O ponto confirmado indica até ",
        "ℹ️ A nova volta é uma inferência operacional; uma confirmação de passagem tem prioridade.",
    )

    linhas = []
    for linha in texto.splitlines():
        limpa = linha.strip()
        if any(limpa.startswith(prefixo) for prefixo in remover_prefixos):
            continue
        linhas.append(linha)

    saida = []
    vazio_anterior = False
    for linha in linhas:
        vazio = not linha.strip()
        if vazio and vazio_anterior:
            continue
        saida.append(linha)
        vazio_anterior = vazio
    return "\n".join(saida).strip()


_base_entry.teclado_menu_com_controle = teclado_menu_ajuste_manual
_base_entry.teclado_localizacao = teclado_localizacao_limpo


class Default(_entry.Default):
    async def _onde(self, chat_id, telegram_id=None):
        principal = await self._estado().localizacao()
        texto_principal = _enxugar_texto_usuario(principal["texto"])
        texto = "🚌 <b>CIRCULAR PRINCIPAL</b>\n\n" + texto_principal

        avisos = await self._avisos_ativos()
        impacto = _core.impacto_localizacao(avisos)
        if impacto:
            texto += "\n\n" + impacto

        status = await self._status_micro()
        if status.get("ativo"):
            micro = await self._estado().localizacao_micro()
            estado_micro = micro.get("estado") or {}
            texto_micro = (
                micro.get("texto")
                if estado_micro.get("horario") and estado_micro.get("ponto_atual")
                else _core.referencia_micro_sem_ponto()
            )
            texto_micro = _enxugar_texto_usuario(texto_micro)
            texto += "\n\n────────────\n\n🚐 <b>MICRO — REFORÇO</b>\n\n" + texto_micro

        return await _core.enviar_mensagem(
            self.env.TELEGRAM_BOT_TOKEN,
            chat_id,
            texto,
            parse_mode="HTML",
            reply_markup=teclado_localizacao_limpo(self._telegram_admin(telegram_id)),
        )

    async def _horarios(self, chat_id):
        dados = await self._estado().resumo_horarios()
        texto = _enxugar_texto_usuario(dados["texto"])
        status = await self._status_micro()
        if status.get("ativo"):
            texto = _core.limitar_resumo_principal(texto, 2) + "\n\n" + _core.resumo_micro()
        return await _core.enviar_mensagem(
            self.env.TELEGRAM_BOT_TOKEN,
            chat_id,
            _enxugar_texto_usuario(texto),
            parse_mode="HTML",
            reply_markup=_core.teclado_voltar(),
        )

    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao == "onde":
            return await self._onde(chat_id, telegram_id)

        if acao == "horarios":
            return await self._horarios(chat_id)

        if acao == "admin_ajuste_menu":
            if not self._telegram_admin(telegram_id):
                return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            return await _core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "🛠️ Ajuste manual\n\nEscolha o que deseja corrigir:",
                reply_markup=teclado_ajuste_manual(),
            )
        return await super()._acao(acao, chat_id, telegram_id)
