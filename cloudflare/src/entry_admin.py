import entry as _entry
from entry import *

from dados import PONTOS, ROTA, ROTULOS_PONTOS


_SENTIDOS_ROTULO = {
    "RUA": "➡️ Rua",
    "RU": "⬅️ RU",
    "GARAGEM": "🅿️ Garagem",
}


_teclado_localizacao_original = _entry.teclado_localizacao
_teclado_menu_original = _entry.teclado_menu_com_controle


def teclado_localizacao_admin(admin=False):
    teclado = _teclado_localizacao_original(admin)
    if not admin:
        return teclado
    linhas = list(teclado.get("inline_keyboard", []))
    botao = [{"text": "🛠️ Corrigir ponto / sentido", "callback_data": "admin_corrigir_menu"}]
    indice_voltar = max(0, len(linhas) - 1)
    linhas.insert(indice_voltar, botao)
    return {"inline_keyboard": linhas}


def teclado_menu_admin(micro_ativo=False, admin=False, principal_ativo=True):
    teclado = _teclado_menu_original(micro_ativo, admin, principal_ativo)
    if not admin:
        return teclado
    linhas = list(teclado.get("inline_keyboard", []))
    botao = [{"text": "🛠️ Corrigir ponto / sentido", "callback_data": "admin_corrigir_menu"}]
    indice_ajuda = next(
        (i for i, linha in enumerate(linhas) if any(b.get("callback_data") == "ajuda" for b in linha)),
        len(linhas),
    )
    linhas.insert(indice_ajuda, botao)
    return {"inline_keyboard": linhas}


_entry.teclado_localizacao = teclado_localizacao_admin
_entry.teclado_menu_com_controle = teclado_menu_admin


def teclado_pontos_correcao():
    botoes = []
    for ponto_id, ponto in PONTOS.items():
        if ponto_id == "garagem":
            continue
        botoes.append({
            "text": ROTULOS_PONTOS.get(ponto_id, ponto["nome"]),
            "callback_data": f"admin_corrigir_ponto_{ponto_id}",
        })
    linhas = [botoes[i:i + 2] for i in range(0, len(botoes), 2)]
    linhas.append([{"text": "⬅️ Voltar", "callback_data": "onde"}])
    return {"inline_keyboard": linhas}


def sentidos_disponiveis(ponto_id):
    sentidos = []
    for item in ROTA:
        if item["ponto_id"] != ponto_id:
            continue
        sentido = item.get("sentido_apos")
        if sentido and sentido not in sentidos:
            sentidos.append(sentido)
    if ponto_id in {"fitotecnia", "solos_neas_florestal"}:
        sentidos.append("GARAGEM")
    return sentidos


def teclado_sentidos_correcao(ponto_id):
    linhas = [
        [{
            "text": _SENTIDOS_ROTULO[sentido],
            "callback_data": f"admin_corrigir_sentido_{ponto_id}_{sentido}",
        }]
        for sentido in sentidos_disponiveis(ponto_id)
    ]
    linhas.append([{"text": "⬅️ Escolher outro ponto", "callback_data": "admin_corrigir_menu"}])
    return {"inline_keyboard": linhas}


class Default(_entry.Default):
    async def _acao(self, acao, chat_id, telegram_id=None):
        if acao == "admin_corrigir_menu":
            if not self._telegram_admin(telegram_id):
                return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            return await _entry._core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "🛠️ Correção administrativa\n\nEscolha o ponto que deve substituir a última confirmação:",
                reply_markup=teclado_pontos_correcao(),
            )

        if acao.startswith("admin_corrigir_ponto_"):
            if not self._telegram_admin(telegram_id):
                return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            ponto_id = acao.replace("admin_corrigir_ponto_", "", 1)
            if ponto_id not in PONTOS or ponto_id == "garagem":
                return await _entry._core.enviar_mensagem(
                    self.env.TELEGRAM_BOT_TOKEN,
                    chat_id,
                    "⚠️ Ponto inválido.",
                    reply_markup=teclado_pontos_correcao(),
                )
            sentidos = sentidos_disponiveis(ponto_id)
            if not sentidos:
                return await _entry._core.enviar_mensagem(
                    self.env.TELEGRAM_BOT_TOKEN,
                    chat_id,
                    "⚠️ Não há sentido configurado para esse ponto.",
                    reply_markup=teclado_pontos_correcao(),
                )
            nome = ROTULOS_PONTOS.get(ponto_id, PONTOS[ponto_id]["nome"])
            return await _entry._core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                f"📍 Ponto: {nome}\n\nAgora escolha o sentido correto:",
                reply_markup=teclado_sentidos_correcao(ponto_id),
            )

        if acao.startswith("admin_corrigir_sentido_"):
            if not self._telegram_admin(telegram_id):
                return {"ok_http": True, "status": 200, "telegram": {"ok": True}}
            bruto = acao.replace("admin_corrigir_sentido_", "", 1)
            try:
                ponto_id, sentido = bruto.rsplit("_", 1)
            except ValueError:
                ponto_id, sentido = "", ""
            if sentido not in sentidos_disponiveis(ponto_id):
                return await _entry._core.enviar_mensagem(
                    self.env.TELEGRAM_BOT_TOKEN,
                    chat_id,
                    "⚠️ Combinação de ponto e sentido inválida.",
                    reply_markup=teclado_pontos_correcao(),
                )

            resultado = await self._estado().corrigir_ponto_sentido_admin(ponto_id, sentido)
            if not resultado.get("ok"):
                return await _entry._core.enviar_mensagem(
                    self.env.TELEGRAM_BOT_TOKEN,
                    chat_id,
                    "⚠️ Não consegui aplicar essa correção.",
                    reply_markup=teclado_pontos_correcao(),
                )

            return await _entry._core.enviar_mensagem(
                self.env.TELEGRAM_BOT_TOKEN,
                chat_id,
                "✅ Localização corrigida manualmente.\n\n"
                f"📍 {resultado['ponto']}\n"
                f"{_SENTIDOS_ROTULO.get(resultado['sentido'], resultado['sentido'])}\n\n"
                "📌 A correção passa a ser a confirmação mais recente do circular.",
                reply_markup=teclado_localizacao_admin(True),
            )

        return await super()._acao(acao, chat_id, telegram_id)
