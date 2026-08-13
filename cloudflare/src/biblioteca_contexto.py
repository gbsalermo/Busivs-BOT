from dados import PONTOS, ROTA
from regras import _minutos, _proximo, _ultima_saida_recente, estimar_chegada_portao_1, montar_localizacao


MARCADOR_FIM_BLOCO = "operacao_encerrada_bloco"
DIAS_SEMANA = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]


def _resultado_para_indice(indice, sentido, ponto_id="biblioteca", estimado_por_horario=True):
    return {
        "ponto_anterior": None,
        "ponto_atual": PONTOS[ponto_id]["nome"],
        "ponto_atual_id": ponto_id,
        "indice_atual": indice,
        "sentido": sentido,
        "proximo": _proximo(indice),
        "estimado_por_horario": estimado_por_horario,
    }


def _indice_biblioteca_por_sentido(sentido):
    for i, item in enumerate(ROTA):
        if item["ponto_id"] == "biblioteca" and item.get("sentido_apos") == sentido:
            return i
    return None


def ajustar_primeira_biblioteca(estado, resultado_registro, agora):
    """Resolve Biblioteca quando ela é a primeira confirmação da sessão."""
    if not resultado_registro.get("aceito"):
        return estado
    if not resultado_registro.get("primeiro_registro"):
        return estado
    if estado.get("ponto_atual") != "biblioteca":
        return estado

    saida = _ultima_saida_recente(agora)
    if not saida:
        estado["resultado_rota"] = {
            "ponto_atual_id": "biblioteca",
            "biblioteca_ambigua": True,
            "motivo": "sem_saida_recente",
        }
        return estado

    previsao = estimar_chegada_portao_1(saida["hora"])
    agora_min = agora.hour * 60 + agora.minute
    inicio_p1 = _minutos(previsao["inicio"])
    fim_p1 = _minutos(previsao["fim"])

    if agora_min < inicio_p1:
        sentido = "RUA"
    elif agora_min > fim_p1:
        sentido = "RU"
    else:
        estado["resultado_rota"] = {
            "ponto_atual_id": "biblioteca",
            "biblioteca_ambigua": True,
            "saida_referencia": saida["hora"],
            "janela_portao_1": [previsao["inicio"], previsao["fim"]],
        }
        return estado

    indice = _indice_biblioteca_por_sentido(sentido)
    if indice is None:
        return estado

    resultado = _resultado_para_indice(indice, sentido)
    resultado["saida_referencia"] = saida["hora"]
    resultado["janela_portao_1"] = [previsao["inicio"], previsao["fim"]]
    estado["resultado_rota"] = resultado
    return estado


def ajustar_primeiro_ponto(estado, resultado_registro, agora):
    """Define o sentido imediatamente quando o primeiro ponto é inequívoco.

    Biblioteca continua recebendo tratamento temporal porque aparece na ida e no
    retorno. RU também permanece sem sentido forçado porque representa tanto o
    início quanto o fim de uma volta. Nos demais pontos, a posição na rota já é
    suficiente: por exemplo Portão 2 implica ida/RUA e Portão 1 implica retorno/RU.
    """
    if not resultado_registro.get("aceito") or not resultado_registro.get("primeiro_registro"):
        return estado

    ponto_id = estado.get("ponto_atual")
    if ponto_id == "biblioteca":
        return ajustar_primeira_biblioteca(estado, resultado_registro, agora)
    if ponto_id == "ru":
        return estado

    ocorrencias = [i for i, item in enumerate(ROTA) if item["ponto_id"] == ponto_id]
    if len(ocorrencias) != 1:
        return estado

    indice = ocorrencias[0]
    item = ROTA[indice]
    estado["resultado_rota"] = _resultado_para_indice(
        indice,
        item["sentido_apos"],
        ponto_id=ponto_id,
        estimado_por_horario=False,
    )
    return estado


def _texto_bloco_encerrado(resultado):
    linhas = [
        "🅿️ O circular provavelmente já retornou à Garagem.",
        "🚌 A última volta deste bloco já encerrou pelo horário previsto.",
    ]

    if resultado.get("fim_do_dia"):
        linhas += ["", "🌙 As viagens de hoje já encerraram."]
    else:
        proxima = resultado.get("proxima") or {}
        if proxima.get("hora"):
            linhas += [
                "",
                "⏰ Próxima saída prevista:",
                f"     🕐 {proxima['hora']} — {proxima.get('origem', 'Garagem')}",
            ]

    linhas += [
        "",
        "ℹ️ Situação estimada pelo horário, sem confirmação recente de passagem.",
    ]
    return "\n".join(linhas)


def texto_sem_operacao(contexto):
    """Monta a resposta do principal quando não há bloco ativo."""
    tipo = contexto.get("tipo")
    proxima = contexto.get("proxima") or {}
    quando = proxima.get("quando")
    viagem = proxima.get("viagem") or {}
    hora = viagem.get("hora") or (quando.strftime("%H:%M") if quando else "--:--")
    origem = viagem.get("origem", "Garagem")

    if tipo == "pre_saida":
        segundos = max(0, int(contexto.get("faltam_segundos", 0)))
        minutos = max(1, (segundos + 59) // 60)
        return (
            "🅿️ Ônibus provavelmente na Garagem.\n\n"
            f"⏰ Saída prevista em aproximadamente {minutos} min.\n"
            f"🕐 Volta das {hora} — {origem}\n\n"
            "ℹ️ Horário oficial; pode haver atraso na saída."
        )

    if tipo == "entre_blocos":
        linhas = [
            "🅿️ O circular provavelmente está na Garagem.",
            "🚌 A volta anterior já encerrou.",
        ]
    elif tipo == "antes_primeiro":
        linhas = [
            "🌙 A rotina anterior do circular já encerrou.",
            "🅿️ O ônibus provavelmente está na Garagem.",
        ]
    elif tipo == "fim_semana":
        linhas = [
            "📅 O circular não possui operação regular aos fins de semana.",
            "🅿️ O ônibus provavelmente está na Garagem.",
        ]
    else:
        linhas = [
            "🌙 A rotina do circular de hoje já encerrou.",
            "🅿️ O ônibus provavelmente está na Garagem.",
        ]

    linhas += ["", "⏰ Próxima saída prevista:"]

    if quando:
        if proxima.get("mesmo_dia"):
            linhas.append(f"     🕐 Hoje às {hora} — {origem}")
        else:
            dia = DIAS_SEMANA[quando.weekday()]
            linhas.append(f"     🕐 {dia}, {quando.strftime('%d/%m')} às {hora} — {origem}")
    else:
        linhas.append(f"     🕐 {hora} — {origem}")

    linhas += [
        "",
        "ℹ️ Situação estimada pela rotina oficial; não há localização colaborativa ativa neste período.",
    ]
    return "\n".join(linhas)


def montar_localizacao_com_biblioteca(estado, agora):
    resultado = estado.get("resultado_rota") or {}

    if resultado.get(MARCADOR_FIM_BLOCO):
        return estado, _texto_bloco_encerrado(resultado)

    if estado.get("ponto_atual") == "biblioteca" and resultado.get("biblioteca_ambigua"):
        horario = estado.get("horario")
        hora_txt = "--:--"
        if horario:
            try:
                from datetime import datetime
                hora_txt = datetime.fromisoformat(horario).strftime("%H:%M:%S")
            except Exception:
                pass

        janela = resultado.get("janela_portao_1")
        referencia = resultado.get("saida_referencia")
        linhas = [
            "📍 Última confirmação: Biblioteca",
            f"🕐 {hora_txt}",
            "",
            "↔️ Sentido ainda indeterminado.",
            "ℹ️ A Biblioteca aparece na ida e no retorno da rota.",
        ]
        if referencia and janela:
            linhas += [
                f"🕐 Volta de referência: {referencia}",
                f"🚪 Janela prevista do Portão 1: {janela[0]}–{janela[1]}",
            ]
        linhas += [
            "📍 Uma nova confirmação em outro ponto definirá o sentido com prioridade sobre a estimativa.",
        ]
        return estado, "\n".join(linhas)

    return montar_localizacao(estado, agora)
