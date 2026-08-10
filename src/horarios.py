import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

CAMINHO_HORARIOS = Path(__file__).resolve().parent.parent / "data" / "horarios_letivo.json"
FUSO_LOCAL = timezone(timedelta(hours=-3))

TITULOS_PERIODOS = {
    "manha": "🌅 <b>Manhã</b>",
    "meio_dia": "🍽️ <b>Almoço</b>",
    "tarde": "🌤️ <b>Tarde</b>",
    "noite": "🌙 <b>Noite</b>",
}

ORIGEM_RETORNO = "Portão 1"


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


def _icone_origem(origem: str) -> str:
    origem_normalizada = origem.strip().lower()

    if "ru" in origem_normalizada:
        return "🍽️"
    if "portão 1" in origem_normalizada or "portao 1" in origem_normalizada:
        return "🚪"
    if "garagem" in origem_normalizada:
        return "🅿️"

    return "📍"


def _sentido_por_origem(origem: str) -> str:
    origem_normalizada = origem.strip().lower()

    if "portão 1" in origem_normalizada or "portao 1" in origem_normalizada:
        return "RU"

    return "Rua"


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

    if pico:
        minimo = 20
        maximo = 25
    else:
        minimo = 15
        maximo = 20

    return {
        "inicio": _formatar_minutos(minutos_saida + minimo),
        "fim": _formatar_minutos(minutos_saida + maximo),
        "pico": pico,
        "noturno": minutos_saida >= _minutos("20:00"),
    }


def _linhas_previsao_portao_1(hora_saida: str) -> list[str]:
    previsao = estimar_chegada_portao_1(hora_saida)

    linhas = [
        f"🚪 <b>Previsão no Portão 1:</b> "
        f"<code>{previsao['inicio']}</code>–<code>{previsao['fim']}</code>"
    ]

    if previsao["pico"]:
        linhas.append("⚠️ <i>Horário de pico: pode haver atrasos.</i>")
    elif previsao["noturno"]:
        linhas.append("🌙 <i>À noite o trajeto pode levar menos tempo.</i>")

    return linhas


def proximo_horario(veiculo: str = "principal", agora: datetime | None = None) -> dict | None:
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])

    if not horarios:
        return None

    agora = agora or datetime.now(FUSO_LOCAL)
    minutos_agora = agora.hour * 60 + agora.minute

    for horario in horarios:
        if _minutos(horario["hora"]) >= minutos_agora:
            return horario

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

    indice = horarios.index(proximo)
    depois = horarios[indice + 1] if indice + 1 < len(horarios) else None

    origem = proximo["origem"]
    sentido = _sentido_por_origem(origem)

    linhas = [
        f"🚌 <b>Circular UFRB — {nome}</b>",
        "",
        "🟢 <b>PRÓXIMA SAÍDA</b>",
        f"🕐 <code>{proximo['hora']}</code>",
        f"{_icone_origem(origem)} <b>Origem:</b> {origem}",
        f"🧭 <b>Sentido:</b> {sentido}",
    ]
    linhas.extend(_linhas_previsao_portao_1(proximo["hora"]))

    if depois:
        origem_depois = depois["origem"]
        linhas.extend(
            [
                "",
                "⏭️ <b>SAÍDA SEGUINTE</b>",
                f"🕐 <code>{depois['hora']}</code>",
                f"{_icone_origem(origem_depois)} <b>Origem:</b> {origem_depois}",
                f"🧭 <b>Sentido:</b> {_sentido_por_origem(origem_depois)}",
            ]
        )
        linhas.extend(_linhas_previsao_portao_1(depois["hora"]))

    linhas.extend(
        [
            "",
            f"↩️ <b>Retorno:</b> {ORIGEM_RETORNO} → <b>RU</b>",
            "",
            "ℹ️ <i>As previsões são estimativas baseadas no tempo médio do trajeto e podem variar.</i>",
            "",
            f"🕐 <b>Primeiro horário:</b> <code>{primeiro['hora']}</code>",
            f"🌙 <b>Último horário:</b> <code>{ultimo['hora']}</code>",
        ]
    )

    return "\n".join(linhas)


def listar_horarios_periodo(periodo: str, veiculo: str = "principal") -> str:
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])
    nome = "Principal" if veiculo == "principal" else "Micro"

    horarios_periodo = [
        horario for horario in horarios if _pertence_ao_periodo(horario["hora"], periodo)
    ]

    if not horarios_periodo:
        return f"📋 <b>{nome}</b>\n\nNenhum horário cadastrado para este período."

    linhas = [
        f"🚌 <b>Circular UFRB — {nome}</b>",
        TITULOS_PERIODOS.get(periodo, periodo.title()),
        "",
        "🟢 <b>SAÍDA DO RU</b> <i>(sentido Rua)</i>",
        "",
    ]

    for horario in horarios_periodo:
        previsao = estimar_chegada_portao_1(horario["hora"])
        indicador = "⚠️" if previsao["pico"] else "🚪"

        linhas.append(
            f"🍽️ <code>{horario['hora']}</code>  RU → Rua\n"
            f"   {indicador} Portão 1: <code>{previsao['inicio']}</code>–<code>{previsao['fim']}</code>"
        )

        if previsao["pico"]:
            linhas.append("   <i>Horário de pico — pode atrasar.</i>")
        elif previsao["noturno"]:
            linhas.append("   <i>À noite pode chegar antes da estimativa.</i>")

        linhas.append("")

    linhas.extend(
        [
            "🔴 <b>RETORNO</b> <i>(sentido RU)</i>",
            f"🚪 <b>Origem:</b> {ORIGEM_RETORNO}",
            "🧭 <b>Sentido:</b> RU",
            "",
            "ℹ️ <i>Previsões aproximadas; trânsito e lotação podem alterar o tempo.</i>",
        ]
    )

    return "\n".join(linhas)
