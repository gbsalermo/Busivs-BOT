import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

CAMINHO_HORARIOS = Path(__file__).resolve().parent.parent / "data" / "horarios_letivo.json"
FUSO_LOCAL = timezone(timedelta(hours=-3))
MARGEM_RETORNO_MINUTOS = 5
DURACAO_RETORNO_MINUTOS = 15

TITULOS_PERIODOS = {
    "manha": "🌅 <b>Horários da manhã</b>",
    "meio_dia": "🍽️ <b>Horários do almoço</b>",
    "tarde": "🌤️ <b>Horários da tarde</b>",
    "noite": "🌙 <b>Horários da noite</b>",
}

NOMES_PERIODOS = {
    "manha": "manhã",
    "meio_dia": "almoço",
    "tarde": "tarde",
    "noite": "noite",
}

FAIXAS_PICO_PERIODOS = {
    "manha": "07:40–08:20 e 11:30–12:45",
    "meio_dia": "11:30–14:00",
    "tarde": "13:00–14:00",
    "noite": "17:30–18:40",
}


def carregar_horarios() -> dict:
    with CAMINHO_HORARIOS.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _minutos(horario: str) -> int:
    hora, minuto = map(int, horario.split(":"))
    return hora * 60 + minuto


def _formatar_minutos(total_minutos: int) -> str:
    total_minutos %= 24 * 60
    hora = total_minutos // 60
    minuto = total_minutos % 60
    return f"{hora:02d}:{minuto:02d}"


def _nome_origem(origem: str) -> str:
    origem_normalizada = origem.strip().lower()

    if "ru" in origem_normalizada:
        return "RU"
    if "garagem" in origem_normalizada:
        return "Garagem"

    return origem


def _icone_origem(origem: str) -> str:
    origem_normalizada = origem.strip().lower()

    if "ru" in origem_normalizada:
        return "🍽️"
    if "garagem" in origem_normalizada:
        return "🅿️"
    if "portão 1" in origem_normalizada or "portao 1" in origem_normalizada:
        return "🚪"

    return "📍"


def _pertence_ao_periodo(hora: str, periodo: str) -> bool:
    minutos = _minutos(hora)

    if periodo == "manha":
        return minutos <= _minutos("12:20")

    if periodo == "meio_dia":
        return _minutos("11:30") <= minutos <= _minutos("13:25")

    if periodo == "tarde":
        return _minutos("13:00") <= minutos < _minutos("17:30")

    if periodo == "noite":
        return minutos >= _minutos("17:30")

    return False


def _periodo_por_hora(agora: datetime) -> tuple[str, str]:
    minutos = agora.hour * 60 + agora.minute

    if minutos < _minutos("11:30"):
        return "🌅", "Manhã"
    if minutos < _minutos("13:00"):
        return "🍽️", "Almoço"
    if minutos < _minutos("17:30"):
        return "🌤️", "Tarde"
    return "🌙", "Noite"


def _eh_horario_pico(hora: str) -> bool:
    minutos = _minutos(hora)

    return (
        _minutos("07:30") <= minutos <= _minutos("08:00")
        or _minutos("11:30") <= minutos <= _minutos("14:00")
        or _minutos("17:30") <= minutos <= _minutos("18:15")
    )


def estimar_chegada_portao_1(hora_saida: str) -> dict:
    minutos_saida = _minutos(hora_saida)
    pico = _eh_horario_pico(hora_saida)

    minimo = 20 if pico else 15
    maximo = 25 if pico else 20

    return {
        "inicio": _formatar_minutos(minutos_saida + minimo),
        "fim": _formatar_minutos(minutos_saida + maximo),
        "pico": pico,
        "noturno": minutos_saida >= _minutos("20:00"),
    }


def _formatar_viagem(horario: dict) -> list[str]:
    hora = horario["hora"]
    origem = horario["origem"]
    nome_origem = _nome_origem(origem)
    previsao = estimar_chegada_portao_1(hora)

    alerta = " ⚠️ (horário de pico)" if previsao["pico"] else ""
    linhas = [
        f"🕒 <code>{hora}</code> · {nome_origem} → Rua{alerta}",
        f"🚪 Portão 1: <code>{previsao['inicio']}</code>–<code>{previsao['fim']}</code>",
    ]

    if previsao["noturno"] and not previsao["pico"]:
        linhas.append("🌙 <i>À noite pode chegar antes da estimativa.</i>")

    return linhas


def viagem_em_andamento(veiculo: str = "principal", agora: datetime | None = None) -> dict | None:
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])

    if not horarios:
        return None

    agora = agora or datetime.now(FUSO_LOCAL)
    minutos_agora = agora.hour * 60 + agora.minute

    candidatos = []
    for horario in horarios:
        minutos_saida = _minutos(horario["hora"])
        previsao = estimar_chegada_portao_1(horario["hora"])
        minutos_fim = _minutos(previsao["fim"])

        if minutos_saida <= minutos_agora <= minutos_fim:
            candidatos.append(horario)

    if not candidatos:
        return None

    return max(candidatos, key=lambda horario: _minutos(horario["hora"]))


def proximo_horario(veiculo: str = "principal", agora: datetime | None = None) -> dict | None:
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])

    if not horarios:
        return None

    agora = agora or datetime.now(FUSO_LOCAL)
    minutos_agora = agora.hour * 60 + agora.minute

    for horario in horarios:
        if _minutos(horario["hora"]) > minutos_agora:
            return horario

    return None


def viagem_em_retorno(veiculo: str = "principal", agora: datetime | None = None) -> dict | None:
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])

    if not horarios:
        return None

    agora = agora or datetime.now(FUSO_LOCAL)
    minutos_agora = agora.hour * 60 + agora.minute

    for indice, horario in enumerate(horarios):
        previsao = estimar_chegada_portao_1(horario["hora"])
        inicio_retorno = _minutos(previsao["fim"]) + MARGEM_RETORNO_MINUTOS
        proxima_saida = (
            _minutos(horarios[indice + 1]["hora"])
            if indice + 1 < len(horarios)
            else 24 * 60
        )
        fim_retorno = min(inicio_retorno + DURACAO_RETORNO_MINUTOS, proxima_saida)

        if inicio_retorno <= minutos_agora < fim_retorno:
            return {
                "viagem": horario,
                "origem": _nome_origem(horario["origem"]),
                "inicio_retorno": _formatar_minutos(inicio_retorno),
                "fim_retorno": _formatar_minutos(fim_retorno),
                "proxima": horarios[indice + 1] if indice + 1 < len(horarios) else None,
            }

    return None


def aguardando_proxima_saida(veiculo: str = "principal", agora: datetime | None = None) -> dict | None:
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])

    if not horarios:
        return None

    agora = agora or datetime.now(FUSO_LOCAL)
    minutos_agora = agora.hour * 60 + agora.minute

    for indice, horario in enumerate(horarios[:-1]):
        previsao = estimar_chegada_portao_1(horario["hora"])
        inicio_retorno = _minutos(previsao["fim"]) + MARGEM_RETORNO_MINUTOS
        fim_retorno = inicio_retorno + DURACAO_RETORNO_MINUTOS
        proxima = horarios[indice + 1]
        proxima_saida = _minutos(proxima["hora"])

        if fim_retorno <= minutos_agora < proxima_saida:
            return {
                "origem": _nome_origem(horario["origem"]),
                "proxima": proxima,
            }

    return None


def montar_resumo_horarios(veiculo: str = "principal", agora: datetime | None = None) -> str:
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])
    nome = "Principal" if veiculo == "principal" else "Micro"

    if not horarios:
        return f"⏰ <b>{nome}</b>\n\nOs horários ainda não foram cadastrados no sistema."

    agora = agora or datetime.now(FUSO_LOCAL)
    primeiro = horarios[0]
    ultimo = horarios[-1]

    if agora.weekday() >= 5:
        return (
            f"🚌 <b>Circular UFRB — {nome}</b>\n\n"
            "O Circular opera de segunda a sexta-feira.\n\n"
            f"🕐 <b>Primeiro horário:</b> <code>{primeiro['hora']}</code>\n"
            f"🌙 <b>Último horário:</b> <code>{ultimo['hora']}</code>"
        )

    proximo = proximo_horario(veiculo, agora)

    if proximo is None:
        return (
            f"🚌 <b>Circular UFRB — {nome}</b>\n\n"
            "As viagens de hoje já encerraram.\n\n"
            f"🕐 <b>Primeiro horário:</b> <code>{primeiro['hora']}</code>\n"
            f"🌙 <b>Último horário:</b> <code>{ultimo['hora']}</code>"
        )

    icone_periodo, nome_periodo = _periodo_por_hora(agora)
    indice = horarios.index(proximo)
    seguintes = horarios[indice + 1:indice + 4]

    linhas = [
        f"🚌 <b>Circular UFRB — {nome}</b>",
        f"{icone_periodo} <b>{nome_periodo}</b>",
        "",
        "🟢 <b>Próxima saída</b>",
    ]
    linhas.extend(_formatar_viagem(proximo))

    if seguintes:
        linhas.extend(["", "📋 <b>Próximos horários</b>"])
        for horario in seguintes:
            previsao = estimar_chegada_portao_1(horario["hora"])
            alerta = " ⚠️ (horário de pico)" if previsao["pico"] else ""
            linhas.extend(
                [
                    f"<code>{horario['hora']}</code> · {_nome_origem(horario['origem'])} → Rua{alerta}",
                    f"🚪 Portão 1: <code>{previsao['inicio']}</code>–<code>{previsao['fim']}</code>",
                ]
            )

    linhas.extend(
        [
            "",
            "ℹ️ <i>Os horários do Portão 1 são previsões e podem variar com trânsito, lotação e atrasos.</i>",
        ]
    )

    return "\n".join(linhas)


def _proxima_saida_do_periodo(horarios_periodo: list[dict], agora: datetime) -> dict | None:
    minutos_agora = agora.hour * 60 + agora.minute

    for horario in horarios_periodo:
        if _minutos(horario["hora"]) >= minutos_agora:
            return horario

    return None


def _formatar_saida_compacta(horario: dict) -> str:
    hora = horario["hora"]
    origem = _nome_origem(horario["origem"])
    previsao = estimar_chegada_portao_1(hora)
    alerta = " ⚠️ (horário de pico)" if previsao["pico"] else ""

    return (
        f"<code>{hora}</code> · {origem}  "
        f"🚪 <code>{previsao['inicio']}</code>–<code>{previsao['fim']}</code>{alerta}"
    )


def listar_horarios_periodo(periodo: str, veiculo: str = "principal") -> str:
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])
    nome = "Principal" if veiculo == "principal" else "Micro"

    horarios_periodo = [
        horario for horario in horarios if _pertence_ao_periodo(horario["hora"], periodo)
    ]

    if not horarios_periodo:
        return f"📋 <b>{nome}</b>\n\nNenhum horário cadastrado para este período."

    agora = datetime.now(FUSO_LOCAL)
    proxima = _proxima_saida_do_periodo(horarios_periodo, agora)
    nome_periodo = NOMES_PERIODOS.get(periodo, "período")

    linhas = [
        f"🚌 <b>Circular UFRB — {nome}</b>",
        TITULOS_PERIODOS.get(periodo, periodo.title()),
        "",
        "➡️ <b>SENTIDO: RUA</b>",
        "🚪 Referência: passagem no Portão 1",
    ]

    if proxima is not None:
        previsao_proxima = estimar_chegada_portao_1(proxima["hora"])
        alerta_proxima = " ⚠️ (horário de pico)" if previsao_proxima["pico"] else ""
        linhas.extend(
            [
                "",
                "🟢 <b>PRÓXIMO ÔNIBUS</b>",
                f"<code>{proxima['hora']}</code> · saída do {_nome_origem(proxima['origem'])}{alerta_proxima}",
                f"🚪 Portão 1: <code>{previsao_proxima['inicio']}</code>–<code>{previsao_proxima['fim']}</code>",
            ]
        )
    else:
        linhas.extend(
            [
                "",
                "✅ Não há mais saídas previstas para este período hoje.",
            ]
        )

    linhas.extend(["", f"📋 <b>Saídas do {nome_periodo}</b>"])

    for horario in horarios_periodo:
        linhas.append(_formatar_saida_compacta(horario))

    if any(estimar_chegada_portao_1(horario["hora"])["pico"] for horario in horarios_periodo):
        faixa_pico = FAIXAS_PICO_PERIODOS.get(periodo)
        linhas.extend(
            [
                "",
                f"⚠️ <b>Horário de pico:</b> {faixa_pico}" if faixa_pico else "⚠️ <b>Há horários de pico neste período.</b>",
                "Pode haver pequenos atrasos.",
            ]
        )
    else:
        linhas.extend(
            [
                "",
                "ℹ️ Horários do Portão 1 são previsões e podem variar.",
            ]
        )

    return "\n".join(linhas)
