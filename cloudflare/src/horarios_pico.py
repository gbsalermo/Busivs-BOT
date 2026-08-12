from datetime import timedelta

from dados import HORARIOS, PONTOS
from regras import (
    _frase_saida,
    _periodo,
    _volta,
    agora_local,
    estimar_chegada_portao_1,
    proximo_horario,
    viagem_em_andamento,
)

TOLERANCIA_PICO_MINUTOS = 5


def _previsto(horario, agora):
    hora, minuto = map(int, horario.split(":"))
    return agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)


def _indice(horario):
    for i, item in enumerate(HORARIOS["principal"]):
        if item["hora"] == horario:
            return i
    return None


def _confirmacao_recente(estado, agora, minutos=30):
    if not estado or not estado.get("horario"):
        return None
    try:
        from datetime import datetime
        momento = datetime.fromisoformat(estado["horario"])
    except Exception:
        return None
    delta = agora - momento
    if delta < timedelta(0) or delta > timedelta(minutes=minutos):
        return None
    return {
        "momento": momento,
        "ponto_id": estado.get("ponto_atual"),
        "resultado_rota": estado.get("resultado_rota"),
    }


def _confirmacao_indica_nova_volta(confirmacao, saida, agora):
    if not confirmacao:
        return False

    inicio = _previsto(saida["hora"], agora)
    if confirmacao["momento"] < inicio:
        return False

    ponto_id = confirmacao.get("ponto_id")
    resultado = confirmacao.get("resultado_rota") or {}

    # RU sozinho é ambíguo: pode ser fim da volta anterior ou início da nova.
    if ponto_id == "ru":
        return False

    # Uma confirmação posterior ao horário oficial em trecho de ida indica
    # que uma nova volta já está efetivamente em deslocamento.
    if resultado.get("sentido") == "RUA":
        return True

    # Para o primeiro registro da sessão ainda pode não haver resultado_rota.
    # Pontos iniciais confirmados depois da saída são evidência suficiente.
    return ponto_id in {
        "fitotecnia",
        "solos_neas_florestal",
        "pavilhao_1",
        "biblioteca",
        "pavilhao_2",
        "pavilhao_engenharia",
        "portao_2",
    }


def _contexto_tolerancia_pico(estado, agora):
    hs = HORARIOS["principal"]
    atual = viagem_em_andamento(agora)
    if atual is None:
        return None

    previsao = estimar_chegada_portao_1(atual["hora"])
    if not previsao["pico"]:
        return None

    inicio = _previsto(atual["hora"], agora)
    decorrido = agora - inicio
    if decorrido < timedelta(0) or decorrido > timedelta(minutes=TOLERANCIA_PICO_MINUTOS):
        return None

    idx = _indice(atual["hora"])
    if idx is None or idx == 0:
        return None

    anterior = hs[idx - 1]
    anterior_pico = estimar_chegada_portao_1(anterior["hora"])["pico"]
    if not anterior_pico:
        return None

    confirmacao = _confirmacao_recente(estado, agora)
    confirmada_nova = _confirmacao_indica_nova_volta(confirmacao, atual, agora)

    return {
        "atual": atual,
        "anterior": anterior,
        "confirmacao": confirmacao,
        "confirmada_nova": confirmada_nova,
        "decorrido_minutos": max(0, int(decorrido.total_seconds() // 60)),
    }


def _linha_confirmacao(confirmacao):
    if not confirmacao or not confirmacao.get("ponto_id"):
        return None
    ponto = PONTOS.get(confirmacao["ponto_id"])
    if not ponto:
        return None
    return f"📍 Última confirmação: {ponto['nome']} às {confirmacao['momento'].strftime('%H:%M')}."


def montar_resumo_horarios(estado=None, agora=None):
    agora = agora or agora_local()
    hs = HORARIOS["principal"]
    primeiro, ultimo = hs[0], hs[-1]

    if agora.weekday() >= 5:
        return (
            "🚌 <b>Circular UFRB — Principal</b>\n\n"
            "O Circular opera de segunda a sexta-feira.\n\n"
            f"🕐 <b>Primeiro horário:</b> <b>{primeiro['hora']}</b>\n"
            f"🌙 <b>Último horário:</b> <b>{ultimo['hora']}</b>"
        )

    atual = viagem_em_andamento(agora)
    prox = proximo_horario(agora)

    if prox is None and atual is None:
        return (
            "🚌 <b>Circular UFRB — Principal</b>\n\n"
            "As viagens de hoje já encerraram.\n\n"
            f"🕐 <b>Primeiro horário:</b> <b>{primeiro['hora']}</b>\n"
            f"🌙 <b>Último horário:</b> <b>{ultimo['hora']}</b>"
        )

    icone, nome_periodo = _periodo(agora)
    linhas = [
        "🚌 <b>Circular UFRB — Principal</b>",
        f"{icone} <b>Horários — {nome_periodo}</b>",
        "",
    ]
    exibidas = []

    tolerancia = _contexto_tolerancia_pico(estado, agora)

    if atual is not None:
        p = estimar_chegada_portao_1(atual["hora"])
        pico = " ⚠️ pico" if p["pico"] else ""

        if tolerancia and not tolerancia["confirmada_nova"]:
            anterior = tolerancia["anterior"]
            linhas += [
                "🟡 <b>Saída prevista</b>",
                f"  {_frase_saida(atual['origem'])}: <b>{atual['hora']}</b>{pico}",
                f"  🚪 Chegada prevista no Portão 1: <b>{p['inicio']}–{p['fim']}</b>",
                "",
                f"⚠️ A volta das <b>{anterior['hora']}</b> pode ainda estar em andamento.",
                f"A saída das <b>{atual['hora']}</b> pode sofrer atraso por consequência da volta anterior.",
            ]
            confirmacao = _linha_confirmacao(tolerancia["confirmacao"])
            if confirmacao:
                linhas.append(confirmacao)
            linhas += [
                "ℹ️ Sem uma confirmação após a nova saída, não é possível afirmar que essa volta já começou.",
                "",
            ]
        else:
            linhas += [
                "🔵 <b>Volta em andamento</b>",
                f"  {_frase_saida(atual['origem'])}: <b>{atual['hora']}</b>{pico}",
                f"  🚪 Chegada prevista no Portão 1: <b>{p['inicio']}–{p['fim']}</b>",
            ]
            if tolerancia and tolerancia["confirmada_nova"]:
                confirmacao = _linha_confirmacao(tolerancia["confirmacao"])
                if confirmacao:
                    linhas.append(f"  ✅ {confirmacao}")
            else:
                linhas.append("  ℹ️ Situação baseada no horário oficial; uma confirmação de ponto tem prioridade.")
            linhas.append("")

        exibidas.append(atual)

    if prox is not None:
        idx = hs.index(prox)
        limite = 3 if atual is not None else 4
        proximas = hs[idx:idx + limite]
        exibidas.extend(proximas)

        for n, horario in enumerate(proximas, 1):
            p = estimar_chegada_portao_1(horario["hora"])
            pico = " ⚠️ pico" if p["pico"] else ""
            if n == 1:
                linhas += [
                    "🟢 <b>Próxima volta</b>",
                    f"  {_frase_saida(horario['origem'])}: <b>{horario['hora']}</b>{pico}",
                    f"  🚪 Chega no Portão 1: <b>{p['inicio']}–{p['fim']}</b>",
                ]
            else:
                linhas += _volta(horario, n)
            if p["noturno"] and not p["pico"]:
                linhas.append("  🌙 À noite pode chegar antes da estimativa.")
            linhas.append("")

    if any(estimar_chegada_portao_1(h["hora"])["pico"] for h in exibidas):
        linhas.append("⚠️ <b>Horários de pico</b> — Pode haver pequenos atrasos e efeito cascata entre voltas próximas.")
    else:
        linhas.append("ℹ️ Horários do Portão 1 são previsões e podem variar.")

    return "\n".join(linhas)
