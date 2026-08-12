from datetime import datetime, timedelta
from dados import HORARIOS
from regras import agora_local


def _horarios_hoje(agora=None):
    agora = agora or agora_local()
    resultado = []
    for item in HORARIOS.get("micro", []):
        h, m = map(int, item["hora"].split(":"))
        resultado.append((agora.replace(hour=h, minute=m, second=0, microsecond=0), item))
    return resultado


def volta_micro_atual(agora=None):
    agora = agora or agora_local()
    horarios = _horarios_hoje(agora)
    anteriores = [(dt, item) for dt, item in horarios if dt <= agora]
    if not anteriores:
        return None
    dt, item = max(anteriores, key=lambda x: x[0])
    # Para teste, cada referência permanece como volta atual até a próxima saída.
    proximas = [x for x in horarios if x[0] > dt]
    limite = min((x[0] for x in proximas), default=dt + timedelta(minutes=30))
    if agora >= limite:
        return None
    return {**item, "inicio": dt}


def proxima_volta_micro(agora=None):
    agora = agora or agora_local()
    proximas = [(dt, item) for dt, item in _horarios_hoje(agora) if dt > agora]
    if not proximas:
        return None
    dt, item = min(proximas, key=lambda x: x[0])
    return {**item, "inicio": dt}


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
        linhas += ["", "⚪ Não há outra referência cadastrada para o micro neste período."]
    return "\n".join(linhas)
