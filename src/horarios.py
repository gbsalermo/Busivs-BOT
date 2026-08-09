import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CAMINHO_HORARIOS = Path(__file__).resolve().parent.parent / "data" / "horarios_letivo.json"
FUSO_LOCAL = ZoneInfo("America/Bahia")


def carregar_horarios() -> dict:
    with CAMINHO_HORARIOS.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _minutos(horario: str) -> int:
    hora, minuto = map(int, horario.split(":"))
    return hora * 60 + minuto


def proximo_horario(veiculo: str = "principal", agora: datetime | None = None) -> str | None:
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])

    if not horarios:
        return None

    agora = agora or datetime.now(FUSO_LOCAL)
    minutos_agora = agora.hour * 60 + agora.minute

    for horario in horarios:
        if _minutos(horario) >= minutos_agora:
            return horario

    return None


def montar_resumo_horarios(veiculo: str = "principal", agora: datetime | None = None) -> str:
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])

    nome = "Principal" if veiculo == "principal" else "Micro"

    if not horarios:
        return (
            f"⏰ {nome}\n\n"
            "Os horários oficiais ainda não foram cadastrados no sistema."
        )

    agora = agora or datetime.now(FUSO_LOCAL)

    if agora.weekday() >= 5:
        return (
            f"⏰ {nome}\n\n"
            "O Circular opera de segunda a sexta-feira.\n\n"
            f"Primeiro horário: {horarios[0]}\n"
            f"Último horário: {horarios[-1]}"
        )

    proximo = proximo_horario(veiculo, agora)

    if proximo is None:
        return (
            f"⏰ {nome}\n\n"
            "As viagens de hoje já encerraram.\n\n"
            f"Primeiro horário: {horarios[0]}\n"
            f"Último horário: {horarios[-1]}"
        )

    indice = horarios.index(proximo)
    depois = horarios[indice + 1] if indice + 1 < len(horarios) else None

    mensagem = (
        f"⏰ {nome}\n\n"
        f"Próxima saída: {proximo}\n"
    )

    if depois:
        mensagem += f"Depois: {depois}\n"

    mensagem += (
        f"\nPrimeiro horário: {horarios[0]}\n"
        f"Último horário: {horarios[-1]}"
    )

    return mensagem
