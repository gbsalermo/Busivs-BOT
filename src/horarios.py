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

    linhas = [
        f"{_icone_origem(origem)} <code>{hora}</code>  {nome_origem} ➡️ <b>RUA</b>",
        f"   ↪️ Retorno Portão 1: <code>{previsao['inicio']}</code>–<code>{previsao['fim']}</code>",
    ]

    if previsao["pico"]:
        linhas.append("   ⚠️ <i>Horário de pico — pode haver atraso.</i>")
    elif previsao["noturno"]:
        linhas.append("   🌙 <i>À noite pode chegar antes da estimativa.</i>")

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

    atual = viagem_em_andamento(veiculo, agora)
    proximo = proximo_horario(veiculo, agora)

    if atual is None and proximo is None:
        return (
            f"🚌 <b>Circular UFRB — {nome}</b>\n\n"
            "As viagens de hoje já encerraram.\n\n"
            f"🕐 <b>Primeiro horário:</b> <code>{primeiro['hora']}</code>\n"
            f"🌙 <b>Último horário:</b> <code>{ultimo['hora']}</code>"
        )

    linhas = [f"🚌 <b>Circular UFRB — {nome}</b>"]

    if atual is not None:
        linhas.extend(
            [
                "",
                "🚌 <b>VOLTA POSSIVELMENTE EM ANDAMENTO</b>",
            ]
        )
        linhas.extend(_formatar_viagem(atual))
        linhas.append("   ℹ️ <i>Situação baseada no horário previsto, não em confirmação de passagem.</i>")

    if proximo is not None:
        linhas.extend(["", "🟢 <b>PRÓXIMA VIAGEM</b>"])
        linhas.extend(_formatar_viagem(proximo))

        indice = horarios.index(proximo)
        depois = horarios[indice + 1] if indice + 1 < len(horarios) else None

        if depois:
            linhas.extend(["", "⏭️ <b>VIAGEM SEGUINTE</b>"])
            linhas.extend(_formatar_viagem(depois))

    linhas.extend(
        [
            "",
            "ℹ️ <i>Horários do Portão 1 são previsões e podem variar com trânsito e lotação.</i>",
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
    ]

    for horario in horarios_periodo:
        linhas.extend(_formatar_viagem(horario))
        linhas.append("")

    linhas.append(
        "ℹ️ <i>Retorno no Portão 1 é uma previsão aproximada e pode variar.</i>"
    )

    return "\n".join(linhas)
