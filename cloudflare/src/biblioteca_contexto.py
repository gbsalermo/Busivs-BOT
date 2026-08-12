from dados import PONTOS, ROTA
from regras import _minutos, _proximo, _ultima_saida_recente, estimar_chegada_portao_1, montar_localizacao


def _resultado_para_indice(indice, sentido, estimado_por_horario=True):
    return {
        "ponto_anterior": None,
        "ponto_atual": PONTOS["biblioteca"]["nome"],
        "ponto_atual_id": "biblioteca",
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
    """Resolve Biblioteca quando ela e a primeira confirmacao da sessao.

    Antes da janela prevista do Portao 1, assume a ocorrencia de ida (RUA).
    Depois da janela, assume a ocorrencia de retorno (RU).
    Dentro da propria janela do Portao 1, mantem o sentido como ambiguo ate
    surgir uma segunda confirmacao.
    """
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


def montar_localizacao_com_biblioteca(estado, agora):
    resultado = estado.get("resultado_rota") or {}
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
