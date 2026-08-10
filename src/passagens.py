import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from horarios import aguardando_proxima_saida, proximo_horario, viagem_em_andamento, viagem_em_retorno
from rota import carregar_pontos, carregar_rota

FUSO_LOCAL = timezone(timedelta(hours=-3))
CAMINHO_HORARIOS = Path(__file__).resolve().parent.parent / "data" / "horarios_letivo.json"
JANELA_SAIDA_GARAGEM_MINUTOS = 35
JANELA_CONFIRMACAO_RECENTE_MINUTOS = 30
LIMITE_INTERVALO_BLOCO_MINUTOS = 60
MAX_HISTORICO_REGISTROS = 20

_estado = {
    "ponto_anterior": None,
    "ponto_atual": None,
    "horario": None,
    "telegram_id": None,
    "resultado_rota": None,
}

_historico_passagens = []


def limpar_estado() -> None:
    _estado.update(
        {
            "ponto_anterior": None,
            "ponto_atual": None,
            "horario": None,
            "telegram_id": None,
            "resultado_rota": None,
        }
    )
    _historico_passagens.clear()


def obter_estado() -> dict:
    return _estado.copy()


def obter_historico() -> list[dict]:
    return [registro.copy() for registro in _historico_passagens]


def _nome_ponto(ponto_id: str) -> str:
    pontos = carregar_pontos()
    ponto = pontos.get(ponto_id)
    return ponto["nome"] if ponto else ponto_id


def _ocorrencias(rota: list[dict], ponto_id: str) -> list[int]:
    return [
        indice
        for indice, item in enumerate(rota)
        if item["ponto_id"] == ponto_id
    ]


def _proximo_da_ocorrencia(rota: list[dict], indice_atual: int, pontos: dict[str, dict]) -> dict | None:
    if indice_atual + 1 >= len(rota):
        return None

    item_proximo = rota[indice_atual + 1]
    ponto_proximo = pontos[item_proximo["ponto_id"]]
    proximo = {
        "id": ponto_proximo["id"],
        "nome": ponto_proximo["nome"],
        "opcional": item_proximo.get("opcional", ponto_proximo.get("opcional", False)),
    }

    if proximo["opcional"]:
        indice_alternativo = indice_atual + 2
        while indice_alternativo < len(rota):
            item_alternativo = rota[indice_alternativo]
            if not item_alternativo.get("opcional", False):
                ponto_alternativo = pontos[item_alternativo["ponto_id"]]
                proximo["alternativa"] = {
                    "id": ponto_alternativo["id"],
                    "nome": ponto_alternativo["nome"],
                }
                break
            indice_alternativo += 1

    return proximo


def _analisar_registros_esparsos(ponto_anterior: str, ponto_atual: str) -> dict | None:
    rota = carregar_rota()
    pontos = carregar_pontos()

    if ponto_anterior not in pontos or ponto_atual not in pontos:
        return None

    anteriores = _ocorrencias(rota, ponto_anterior)
    atuais = _ocorrencias(rota, ponto_atual)

    candidatos = []
    for indice_anterior in anteriores:
        for indice_atual in atuais:
            if indice_atual > indice_anterior:
                candidatos.append((indice_atual - indice_anterior, indice_atual))

    if not candidatos:
        return None

    _, indice_atual = min(candidatos, key=lambda item: item[0])
    item_atual = rota[indice_atual]

    return {
        "ponto_anterior": pontos[ponto_anterior]["nome"],
        "ponto_atual": pontos[ponto_atual]["nome"],
        "ponto_atual_id": ponto_atual,
        "indice_atual": indice_atual,
        "sentido": item_atual["sentido_apos"],
        "proximo": _proximo_da_ocorrencia(rota, indice_atual, pontos),
    }


def _registrar_no_historico(ponto_id: str, horario: datetime, telegram_id: int | None) -> None:
    _historico_passagens.append(
        {
            "ponto_id": ponto_id,
            "horario": horario,
            "telegram_id": telegram_id,
        }
    )

    if len(_historico_passagens) > MAX_HISTORICO_REGISTROS:
        del _historico_passagens[:-MAX_HISTORICO_REGISTROS]


def _resultado_com_historico(ponto_atual: str) -> dict | None:
    """Procura a confirmação anterior mais recente que forme uma sequência válida.

    Um registro incompatível não impede a nova confirmação de ser usada. Ele apenas
    deixa de servir como base para inferir sentido/próximo ponto.
    """
    total = len(_historico_passagens)

    for indice in range(total - 1, -1, -1):
        registro = _historico_passagens[indice]
        ponto_anterior = registro["ponto_id"]

        if ponto_anterior == ponto_atual:
            continue

        resultado = _analisar_registros_esparsos(ponto_anterior, ponto_atual)
        if resultado is None:
            continue

        resultado["base_historico"] = {
            "ponto_id": ponto_anterior,
            "horario": registro["horario"],
            "telegram_id": registro["telegram_id"],
        }
        resultado["ignorou_registro_incompativel"] = indice != total - 1
        return resultado

    return None


def _carregar_horarios_principal() -> list[dict]:
    with CAMINHO_HORARIOS.open("r", encoding="utf-8") as arquivo:
        horarios = json.load(arquivo)

    return horarios.get("principal", [])


def _minutos_horario(hora_texto: str) -> int:
    hora, minuto = map(int, hora_texto.split(":"))
    return hora * 60 + minuto


def _horario_previsto_hoje(hora_texto: str, agora: datetime) -> datetime:
    hora, minuto = map(int, hora_texto.split(":"))
    return agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)


def _quebra_de_bloco_mais_recente(agora: datetime) -> datetime | None:
    horarios = _carregar_horarios_principal()
    quebra_mais_recente = None

    for anterior, proxima in zip(horarios, horarios[1:]):
        intervalo = _minutos_horario(proxima["hora"]) - _minutos_horario(anterior["hora"])
        if intervalo <= LIMITE_INTERVALO_BLOCO_MINUTOS:
            continue

        inicio_novo_bloco = _horario_previsto_hoje(proxima["hora"], agora)
        if inicio_novo_bloco <= agora:
            quebra_mais_recente = inicio_novo_bloco

    return quebra_mais_recente


def _aguardando_em_lacuna_de_bloco(agora: datetime) -> bool:
    aguardando = aguardando_proxima_saida("principal", agora)
    if aguardando is None or aguardando.get("proxima") is None:
        return False

    horarios = _carregar_horarios_principal()
    proxima_hora = aguardando["proxima"]["hora"]

    for indice, horario in enumerate(horarios):
        if horario["hora"] != proxima_hora or indice == 0:
            continue

        anterior = horarios[indice - 1]
        intervalo = _minutos_horario(proxima_hora) - _minutos_horario(anterior["hora"])
        return intervalo > LIMITE_INTERVALO_BLOCO_MINUTOS

    return False


def _ultima_saida_recente_da_garagem(agora: datetime) -> str | None:
    candidatos = []
    for viagem in _carregar_horarios_principal():
        if viagem.get("origem") != "Garagem":
            continue

        previsto = _horario_previsto_hoje(viagem["hora"], agora)
        diferenca = agora - previsto

        if timedelta(0) <= diferenca <= timedelta(minutes=JANELA_SAIDA_GARAGEM_MINUTOS):
            candidatos.append(previsto)

    if not candidatos:
        return None

    return max(candidatos).strftime("%H:%M")


def _estimar_primeiro_registro_por_horario(ponto_id: str, agora: datetime) -> dict | None:
    horario_garagem = _ultima_saida_recente_da_garagem(agora)
    if horario_garagem is None:
        return None

    rota = carregar_rota()
    pontos = carregar_pontos()

    ocorrencias = _ocorrencias(rota, ponto_id)
    if not ocorrencias:
        return None

    indice_atual = None
    for indice in ocorrencias:
        if rota[indice]["sentido_apos"] == "RUA":
            indice_atual = indice
            break

    if indice_atual is None:
        return None

    return {
        "horario_garagem": horario_garagem,
        "sentido": "RUA",
        "proximo": _proximo_da_ocorrencia(rota, indice_atual, pontos),
    }


def _tempo_desde_confirmacao(horario: datetime | None, agora: datetime | None = None) -> str:
    if horario is None:
        return "horário desconhecido"

    agora = agora or datetime.now(FUSO_LOCAL)
    segundos = max(0, int((agora - horario).total_seconds()))

    if segundos < 60:
        return "agora mesmo"

    minutos = segundos // 60
    if minutos < 60:
        return f"há {minutos} min"

    horas = minutos // 60
    minutos_restantes = minutos % 60

    if minutos_restantes == 0:
        return f"há {horas}h"

    return f"há {horas}h {minutos_restantes}min"


def _tem_confirmacao_recente(agora: datetime) -> bool:
    horario = _estado["horario"]
    if horario is None:
        return False

    diferenca = agora - horario
    return timedelta(0) <= diferenca <= timedelta(minutes=JANELA_CONFIRMACAO_RECENTE_MINUTOS)


def _estado_expirou(agora: datetime) -> bool:
    horario = _estado["horario"]
    if horario is None:
        return False

    if horario.date() != agora.date():
        return True

    quebra_recente = _quebra_de_bloco_mais_recente(agora)
    if quebra_recente is not None and horario < quebra_recente:
        return True

    if _aguardando_em_lacuna_de_bloco(agora) and not _tem_confirmacao_recente(agora):
        return True

    return False


def _limpar_estado_se_expirado(agora: datetime) -> None:
    if _estado_expirou(agora):
        limpar_estado()


def _formatar_movimento(resultado: dict) -> str:
    sentido = resultado.get("sentido")
    proximo = resultado.get("proximo")
    seta = "➡️" if sentido == "RUA" else "⬅️"

    linhas = []

    if proximo is None:
        if resultado.get("ponto_atual_id") == "ru":
            linhas.extend(
                [
                    "🏁 Chegada ao RU / fim da volta confirmada.",
                    "🚌 O ônibus pode estar concluindo a volta anterior ou aguardando/iniciando uma nova saída.",
                    "ℹ️ Não é possível afirmar o sentido apenas por esta confirmação; os horários podem sofrer atraso.",
                ]
            )
            return "\n".join(linhas)

        linhas.append("🏁 Fim do percurso cadastrado.")
        linhas.append(f"{seta} Sentido: {sentido}")
        return "\n".join(linhas)

    if proximo["opcional"]:
        linhas.extend(
            [
                "⏭️ Próximo:",
                f"     📍 {proximo['nome']} (se houver parada)",
            ]
        )
        alternativa = proximo.get("alternativa")
        if alternativa:
            linhas.append(f"     ↪️ Caso não pare: {alternativa['nome']}")
    else:
        linhas.extend(
            [
                "⏭️ Próximo:",
                f"     📍 {proximo['nome']}",
            ]
        )

    linhas.append(f"{seta} Sentido: {sentido}")

    return "\n".join(linhas)


def _formatar_retorno(retorno: dict, proxima: dict | None) -> str:
    linhas = [
        "↩️ Percurso de retorno",
        "🚌 Pelo horário, o ônibus provavelmente está no percurso de retorno.",
        f"⬅️ Sentido: {retorno['origem']}",
        "📍 O ônibus ainda segue atendendo pontos durante esse percurso.",
    ]

    if proxima is not None:
        linhas.extend(
            [
                "",
                "⏰ Próxima volta prevista:",
                f"     🕐 {proxima['hora']} — {proxima['origem']}",
            ]
        )

    linhas.append("ℹ️ Situação estimada pelo horário, não por confirmação de passagem.")
    return "\n".join(linhas)


def _formatar_aguardando_saida(aguardando: dict) -> str:
    proxima = aguardando.get("proxima")
    origem = aguardando["origem"]

    linhas = [
        f"🅿️ Provavelmente na {origem}" if origem == "Garagem" else f"📍 Provavelmente no {origem}",
        "🚌 Pelo horário, o ônibus provavelmente já concluiu o percurso anterior.",
    ]

    if proxima is not None:
        linhas.extend(
            [
                "",
                "⏰ Próxima saída prevista:",
                f"     🕐 {proxima['hora']} — {proxima['origem']}",
            ]
        )

    linhas.append("ℹ️ Situação estimada pelo horário, sem confirmação recente de passagem.")
    return "\n".join(linhas)


def _formatar_viagem_sem_confirmacao(viagem: dict) -> str:
    origem = viagem["origem"]
    hora = viagem["hora"]

    return (
        f"🚌 Há uma volta prevista em andamento.\n"
        f"🕐 Saída oficial: {hora} — {origem}\n"
        "➡️ Sentido provável: RUA\n\n"
        "ℹ️ Não há confirmação recente de passagem; o ônibus pode estar adiantado ou atrasado."
    )


def _confirmacao_anterior_ao_retorno(horario: datetime | None, retorno: dict | None) -> bool:
    if horario is None or retorno is None:
        return False

    hora, minuto = map(int, retorno["inicio_retorno"].split(":"))
    inicio_retorno = horario.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    return horario < inicio_retorno


def _possivel_atraso_portao_1(
    ponto_id: str,
    horario_confirmacao: datetime | None,
    resultado_rota: dict | None,
) -> bool:
    if horario_confirmacao is None:
        return False

    if ponto_id not in {"biblioteca", "pavilhao_2"}:
        return False

    if resultado_rota is not None and resultado_rota.get("sentido") != "RUA":
        return False

    inicio = horario_confirmacao.replace(hour=10, minute=15, second=0, microsecond=0)
    fim = horario_confirmacao.replace(hour=10, minute=20, second=59, microsecond=999999)

    return inicio <= horario_confirmacao <= fim


def registrar_passagem(ponto_id: str, telegram_id: int | None = None) -> dict:
    pontos = carregar_pontos()

    if ponto_id not in pontos:
        return {"aceito": False, "motivo": "ponto_invalido"}

    agora = datetime.now(FUSO_LOCAL)
    _limpar_estado_se_expirado(agora)
    aguardando = aguardando_proxima_saida("principal", agora)

    if aguardando is not None and not _tem_confirmacao_recente(agora):
        return {
            "aceito": False,
            "motivo": "fora_circulacao",
            "origem": aguardando["origem"],
            "proxima": aguardando.get("proxima"),
        }

    if _estado["ponto_atual"] == ponto_id:
        return {
            "aceito": False,
            "motivo": "duplicado",
            "ponto": pontos[ponto_id]["nome"],
            "horario": _estado["horario"],
        }

    anterior = _estado["ponto_atual"]
    resultado_rota = _resultado_com_historico(ponto_id)

    if resultado_rota is None and anterior is not None:
        resultado_rota = _analisar_registros_esparsos(anterior, ponto_id)

    _estado.update(
        {
            "ponto_anterior": anterior,
            "ponto_atual": ponto_id,
            "horario": agora,
            "telegram_id": telegram_id,
            "resultado_rota": resultado_rota,
        }
    )
    _registrar_no_historico(ponto_id, agora, telegram_id)

    return {
        "aceito": True,
        "primeiro_registro": anterior is None,
        "ponto": pontos[ponto_id]["nome"],
        "horario": agora,
        "resultado_rota": resultado_rota,
    }


def montar_localizacao_atual() -> str:
    agora = datetime.now(FUSO_LOCAL)
    _limpar_estado_se_expirado(agora)

    atual = viagem_em_andamento("principal", agora)
    retorno = viagem_em_retorno("principal", agora)
    aguardando = aguardando_proxima_saida("principal", agora)
    proxima = proximo_horario("principal", agora)

    if _estado["ponto_atual"] is None:
        if atual is not None:
            return _formatar_viagem_sem_confirmacao(atual)

        if retorno is not None:
            return _formatar_retorno(retorno, proxima)

        if aguardando is not None:
            return _formatar_aguardando_saida(aguardando)

        return (
            "🚌 Ainda não há confirmação de passagem nesta sessão.\n\n"
            "Use 📍 Informar passagem para registrar quando o ônibus passar por um ponto."
        )

    horario = _estado["horario"]
    horario_texto = horario.strftime("%H:%M:%S") if horario else "--:--"
    tempo_texto = _tempo_desde_confirmacao(horario, agora)
    ponto_id = _estado["ponto_atual"]
    ponto_nome = _nome_ponto(ponto_id)
    resultado = _estado["resultado_rota"]

    linhas = [
        f"📍 Última confirmação: {ponto_nome}",
        f"🕐 {tempo_texto} ({horario_texto})",
    ]

    if retorno is not None and _confirmacao_anterior_ao_retorno(horario, retorno):
        linhas.extend(["", _formatar_retorno(retorno, proxima)])
    else:
        if _possivel_atraso_portao_1(ponto_id, horario, resultado):
            linhas.extend(
                [
                    "",
                    "⚠️ Possível atraso no Portão 1",
                    "🚪 Passagem esperada por volta de 10:20.",
                    f"📍 O ônibus ainda foi confirmado em {ponto_nome}.",
                    "ℹ️ É uma estimativa, não uma confirmação de atraso.",
                ]
            )

        if resultado is not None:
            linhas.extend(["", _formatar_movimento(resultado)])
        else:
            estimativa = _estimar_primeiro_registro_por_horario(ponto_id, horario)

            if estimativa is not None:
                linhas.extend(
                    [
                        "",
                        f"🕐 Pelo horário oficial, o ônibus deve ter saído da Garagem às {estimativa['horario_garagem']}.",
                        "➡️ Sentido provável: RUA",
                    ]
                )

                proximo = estimativa.get("proximo")
                if proximo:
                    if proximo["opcional"]:
                        linhas.extend(
                            [
                                "⏭️ Próximo esperado:",
                                f"     📍 {proximo['nome']} (se houver parada)",
                            ]
                        )
                        alternativa = proximo.get("alternativa")
                        if alternativa:
                            linhas.append(f"     ↪️ Caso não pare: {alternativa['nome']}")
                    else:
                        linhas.extend(
                            [
                                "⏭️ Próximo esperado:",
                                f"     📍 {proximo['nome']}",
                            ]
                        )

                linhas.append("ℹ️ Essa indicação usa o horário previsto, não uma confirmação de saída.")
            else:
                linhas.extend(
                    [
                        "",
                        "ℹ️ Ainda preciso de outra confirmação em um ponto diferente",
                        "para estimar o sentido e o próximo ponto.",
                    ]
                )

    return "\n".join(linhas)
