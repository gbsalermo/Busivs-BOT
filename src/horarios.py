import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

CAMINHO_HORARIOS = Path(__file__).resolve().parent.parent / "data" / "horarios_letivo.json"
FUSO_LOCAL = timezone(timedelta(hours=-3))

TITULOS_PERIODOS = {
    "manha": "🌅 Manhã",
    "meio_dia": "🍽️ Almoço",
    "tarde": "🌤️ Tarde",
    "noite": "🌙 Noite",
}


def carregar_horarios() -> dict:
    with CAMINHO_HORARIOS.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _minutos(horario: str) -> int:
    hora, minuto = map(int, horario.split(":"))
    return hora * 60 + minuto


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
        return f"⏰ {nome}\n\nOs horários ainda não foram cadastrados no sistema."

    agora = agora or datetime.now(FUSO_LOCAL)
    primeiro = horarios[0]
    ultimo = horarios[-1]

    if agora.weekday() >= 5:
        return (
            f"⏰ {nome}\n\n"
            "O Circular opera de segunda a sexta-feira.\n\n"
            f"Primeiro horário: {primeiro['hora']} - {primeiro['origem']}\n"
            f"Último horário: {ultimo['hora']} - {ultimo['origem']}"
        )

    proximo = proximo_horario(veiculo, agora)

    if proximo is None:
        return (
            f"⏰ {nome}\n\n"
            "As viagens de hoje já encerraram.\n\n"
            f"Primeiro horário: {primeiro['hora']} - {primeiro['origem']}\n"
            f"Último horário: {ultimo['hora']} - {ultimo['origem']}"
        )

    indice = horarios.index(proximo)
    depois = horarios[indice + 1] if indice + 1 < len(horarios) else None

    mensagem = (
        f"⏰ {nome}\n\n"
        f"Próxima saída: {proximo['hora']}\n"
        f"Saída de: {proximo['origem']}\n"
    )

    if depois:
        mensagem += f"\nDepois: {depois['hora']} - {depois['origem']}\n"

    mensagem += (
        f"\nPrimeiro horário: {primeiro['hora']}\n"
        f"Último horário: {ultimo['hora']}"
    )

    return mensagem


def listar_horarios_periodo(periodo: str, veiculo: str = "principal") -> str:
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])
    nome = "Principal" if veiculo == "principal" else "Micro"

    horarios_periodo = [
        horario for horario in horarios if horario.get("periodo") == periodo
    ]

    if not horarios_periodo:
        return f"📋 {nome}\n\nNenhum horário cadastrado para este período."

    linhas = [f"{TITULOS_PERIODOS.get(periodo, periodo.title())} - {nome}", ""]

    for horario in horarios_periodo:
        linhas.append(f"{horario['hora']} - {horario['origem']}")

    return "\n".join(linhas)
