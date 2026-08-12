from datetime import timedelta

from dados import HORARIOS
from regras import agora_local


def _momento(hora, agora):
    h, m = map(int, hora.split(":"))
    return agora.replace(hour=h, minute=m, second=0, microsecond=0)


def _horarios_hoje(agora=None):
    agora = agora or agora_local()
    return [(_momento(item["hora"], agora), item) for item in HORARIOS.get("micro", [])]


def volta_micro_atual(agora=None):
    agora = agora or agora_local()
    candidatos = []
    for inicio, item in _horarios_hoje(agora):
        fim = _momento(item.get("fim", item["hora"]), agora)
        if inicio <= agora < fim:
            candidatos.append((inicio, item, fim))
    if not candidatos:
        return None
    inicio, item, fim = max(candidatos, key=lambda x: x[0])
    return {**item, "inicio": inicio, "fim_dt": fim}


def proxima_volta_micro(agora=None):
    agora = agora or agora_local()
    proximas = [(inicio, item) for inicio, item in _horarios_hoje(agora) if inicio > agora]
    if not proximas:
        return None
    inicio, item = min(proximas, key=lambda x: x[0])
    return {**item, "inicio": inicio}


def resumo_micro(agora=None):
    agora = agora or agora_local()
    atual = volta_micro_atual(agora)
    proxima = proxima_volta_micro(agora)
    linhas = ["🚐 <b>Micro — reforço</b>", "✅ Operação informada pela comunidade."]
    if atual:
        linhas += ["", "🔵 <b>Volta de referência atual</b>", f"{atual['inicio'].strftime('%H:%M')} — {atual['origem']}"]
    if proxima:
        linhas += ["", "🟢 <b>Próxima referência</b>", f"{proxima['inicio'].strftime('%H:%M')} — {proxima['origem']}"]
    if not atual and not proxima:
        linhas += ["", "⚪ Não há outra referência oficial do micro neste período."]
    return "\n".join(linhas)
