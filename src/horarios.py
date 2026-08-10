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

ORIGEM_RETORNO = "Guarita Principal"


def carregar_horarios() -> dict:
    with CAMINHO_HORARIOS.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _minutos(horario: str) -> int:
    hora, minuto = map(int, horario.split(":"))
    return hora * 60 + minuto


def _icone_origem(origem: str) -> str:
    origem_normalizada = origem.strip().lower()

    if "ru" in origem_normalizada:
        return "🍽️"
    if "guarita principal" in origem_normalizada:
        return "🚪"
    if "garagem" in origem_normalizada:
        return "🅿️"

    return "📍"


def _sentido_por_origem(origem: str) -> str:
    origem_normalizada = origem.strip().lower()

    if "guarita principal" in origem_normalizada:
        return "RU"

    if "garagem" in origem_normalizada or "ru" in origem_normalizada:
        return "Rua"

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

    linhas.extend(
        [
            "",
            f"↩️ <b>Retorno:</b> {ORIGEM_RETORNO} (Portão 1) → <b>RU</b>",
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
        "🟢 <b>IDA</b> <i>(sentido Rua)</i>",
    ]

    for horario in horarios_periodo:
        origem = horario["origem"]
        linhas.append(
            f"{_icone_origem(origem)} <code>{horario['hora']}</code>  "
            f"{origem}  •  🧭 <b>{_sentido_por_origem(origem)}</b>"
        )

    linhas.extend(
        [
            "",
            "🔴 <b>RETORNO</b> <i>(sentido RU)</i>",
            f"🚪 <b>Origem:</b> {ORIGEM_RETORNO} (Portão 1)",
            "🧭 <b>Sentido:</b> RU",
        ]
    )

    return "\n".join(linhas)
