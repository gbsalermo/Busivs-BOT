from datetime import timedelta

from dados import HORARIOS
from regras import agora_local

# Usuário comum pode confirmar o micro dentro de uma faixa funcional ampliada,
# mesmo quando ele estiver rodando fora de uma volta oficial exata.
ANTECEDENCIA_FAIXA_FUNCIONAL_MIN = 30
FIM_FAIXA_FUNCIONAL_HORA = "13:00"

# Se a ativação ocorrer perto de uma saída oficial, vinculamos a sessão àquela
# referência. Caso contrário, a operação é tratada como esporádica.
JANELA_ASSOCIACAO_REFERENCIA_MIN = 15


def _momento(hora, agora):
    h, m = map(int, hora.split(":"))
    return agora.replace(hour=h, minute=m, second=0, microsecond=0)


def _horarios_hoje(agora=None):
    agora = agora or agora_local()
    return [(_momento(item["hora"], agora), item) for item in HORARIOS.get("micro", [])]


def janelas_operacao_micro(agora=None):
    """Agrupa apenas as referências oficiais do micro em blocos contínuos."""
    agora = agora or agora_local()
    intervalos = []
    for inicio, item in _horarios_hoje(agora):
        fim = _momento(item.get("fim", item["hora"]), agora)
        intervalos.append((inicio, fim))

    if not intervalos:
        return []

    intervalos.sort(key=lambda x: x[0])
    blocos = []
    inicio_bloco, fim_bloco = intervalos[0]

    for inicio, fim in intervalos[1:]:
        if inicio <= fim_bloco:
            if fim > fim_bloco:
                fim_bloco = fim
            continue
        blocos.append({"inicio": inicio_bloco, "fim": fim_bloco})
        inicio_bloco, fim_bloco = inicio, fim

    blocos.append({"inicio": inicio_bloco, "fim": fim_bloco})
    return blocos


def janela_operacao_micro_atual(agora=None):
    agora = agora or agora_local()
    for bloco in janelas_operacao_micro(agora):
        if bloco["inicio"] <= agora < bloco["fim"]:
            return bloco
    return None


def faixa_funcional_micro(agora=None):
    """Faixa em que usuário comum pode informar operação esporádica do micro."""
    agora = agora or agora_local()
    horarios = _horarios_hoje(agora)
    if not horarios:
        return None
    primeiro = min(inicio for inicio, _ in horarios)
    inicio = primeiro - timedelta(minutes=ANTECEDENCIA_FAIXA_FUNCIONAL_MIN)
    fim = _momento(FIM_FAIXA_FUNCIONAL_HORA, agora)
    return {"inicio": inicio, "fim": fim}


def micro_pode_ser_ativado_agora(agora=None):
    agora = agora or agora_local()
    if agora.weekday() >= 5:
        return False
    faixa = faixa_funcional_micro(agora)
    return bool(faixa and faixa["inicio"] <= agora < faixa["fim"])


def referencia_micro_proxima(agora=None):
    """Retorna a saída oficial mais próxima, se estiver a até 15 min dela."""
    agora = agora or agora_local()
    candidatos = []
    limite = timedelta(minutes=JANELA_ASSOCIACAO_REFERENCIA_MIN)
    for inicio, item in _horarios_hoje(agora):
        distancia = abs(agora - inicio)
        if distancia <= limite:
            candidatos.append((distancia, inicio, item))
    if not candidatos:
        return None
    _, inicio, item = min(candidatos, key=lambda x: (x[0], x[1]))
    return {**item, "inicio": inicio}


def micro_pode_operar_agora(agora=None):
    # Mantido por compatibilidade: significa possibilidade funcional, não apenas
    # estar exatamente dentro de uma volta oficial.
    return micro_pode_ser_ativado_agora(agora)


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
