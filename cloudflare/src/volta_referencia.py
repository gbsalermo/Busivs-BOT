from datetime import timedelta

from dados import BLOCOS_PRINCIPAL, HORARIOS
from regras import agora_local, estimar_chegada_portao_1

JANELA_RU_REFERENCIA_MINUTOS = 10
JANELA_RU_REFERENCIA_PICO_MINUTOS = 60


def _momento(hora, referencia):
    hh, mm = map(int, hora.split(":"))
    return referencia.replace(hour=hh, minute=mm, second=0, microsecond=0)


def _origem_ru(viagem):
    origem = (viagem or {}).get("origem", "").strip().lower()
    return "ru" in origem or "resid" in origem


def _indice_hora(hora):
    for i, viagem in enumerate(HORARIOS.get("principal", [])):
        if viagem.get("hora") == hora:
            return i
    return None


def _bloco_da_viagem(hora):
    if not hora:
        return None
    minuto = int(hora[:2]) * 60 + int(hora[3:5])
    for bloco in BLOCOS_PRINCIPAL:
        ini = int(bloco["inicio"][:2]) * 60 + int(bloco["inicio"][3:5])
        fim = int(bloco["ultima"][:2]) * 60 + int(bloco["ultima"][3:5])
        if ini <= minuto <= fim:
            return bloco
    return None


def viagem_por_referencia(estado):
    hora = (estado or {}).get("saida_referencia")
    if not hora:
        return None
    indice = _indice_hora(hora)
    if indice is None:
        return None
    return HORARIOS["principal"][indice]


def ultima_saida_oficial(agora):
    candidatas = []
    for viagem in HORARIOS.get("principal", []):
        momento = _momento(viagem["hora"], agora)
        if momento <= agora:
            candidatas.append((momento, viagem))
    return max(candidatas, key=lambda item: item[0])[1] if candidatas else None


def _janela_referencia_ru(viagem):
    previsao = estimar_chegada_portao_1(viagem["hora"])
    if previsao.get("pico"):
        return JANELA_RU_REFERENCIA_PICO_MINUTOS
    return JANELA_RU_REFERENCIA_MINUTOS


def saida_ru_recente(agora):
    """Associa RU à última saída plausível sem trocar a volta só pelo relógio.

    Em horário de pico a janela é maior porque a volta pode retornar ao RU muito
    depois do previsto. Isso evita que uma chegada atrasada da última volta do
    bloco seja interpretada como pertencente ao bloco/saída seguinte.
    """
    candidatas = []
    for viagem in HORARIOS.get("principal", []):
        if not _origem_ru(viagem):
            continue
        momento = _momento(viagem["hora"], agora)
        atraso = agora - momento
        janela = _janela_referencia_ru(viagem)
        if timedelta(0) <= atraso <= timedelta(minutes=janela):
            candidatas.append((momento, viagem))
    return max(candidatas, key=lambda item: item[0])[1] if candidatas else None


def aplicar_referencia(estado, viagem, manual=False):
    if not estado or not viagem:
        return estado
    estado["saida_referencia"] = viagem["hora"]
    estado["saida_referencia_manual"] = bool(manual)
    return estado


def retornar_volta_anterior(estado, agora):
    horarios = HORARIOS.get("principal", [])
    atual = viagem_por_referencia(estado) or ultima_saida_oficial(agora)
    if atual is None:
        return estado, None
    indice = _indice_hora(atual["hora"])
    if indice is None or indice <= 0:
        return estado, None
    anterior = horarios[indice - 1]
    aplicar_referencia(estado, anterior, manual=True)
    return estado, anterior


def proxima_apos_referencia(estado, agora=None):
    """Retorna a próxima referência somente depois de seu horário oficial.

    Um ponto que indique reinício da rota antes da próxima saída programada não
    deve adiantar a referência. Ex.: após concluir 11:55 no RU, Fitotecnia às
    12:04 ainda pertence ao contexto 11:55; 12:20 só pode virar referência a
    partir de 12:20.
    """
    viagem = viagem_por_referencia(estado)
    if viagem is None:
        return None
    indice = _indice_hora(viagem["hora"])
    if indice is None or indice + 1 >= len(HORARIOS["principal"]):
        return None

    proxima = HORARIOS["principal"][indice + 1]
    referencia_tempo = agora or agora_local()
    if _momento(proxima["hora"], referencia_tempo) > referencia_tempo:
        return None
    return proxima


def _proximas_apos_viagem(viagem, quantidade=3):
    if not viagem:
        return []
    indice = _indice_hora(viagem.get("hora"))
    if indice is None:
        return []
    return HORARIOS.get("principal", [])[indice + 1:indice + 1 + quantidade]


def limite_referencia(estado, agora):
    """Compatibilidade: referências não expiram por horário dentro do bloco."""
    return None


def referencia_ainda_valida(estado, agora):
    return viagem_por_referencia(estado) is not None


def proxima_volta_provavel(estado, agora):
    """Não inferir nova volta apenas porque o relógio passou da próxima saída."""
    return None


def limpar_referencia_expirada(estado, agora):
    """A expiração operacional é responsabilidade do fechamento de bloco."""
    return estado


def _adicionar_proximas(linhas, viagem_base, quantidade=3):
    proximas = _proximas_apos_viagem(viagem_base, quantidade)
    if not proximas:
        return linhas
    linhas += ["", "🟢 <b>Próximas saídas oficiais</b>"]
    for viagem in proximas:
        linhas.append(f"🕐 <b>{viagem['hora']}</b> — {viagem.get('origem', '')}")
    return linhas


def resumo_referenciado(estado, agora, resumo_padrao):
    atual = viagem_por_referencia(estado)
    if atual is None:
        return resumo_padrao

    previsao = estimar_chegada_portao_1(atual["hora"])
    origem = atual.get("origem", "")
    bloco_atual = _bloco_da_viagem(atual["hora"])
    ultima_do_bloco = bool(bloco_atual and bloco_atual.get("ultima") == atual.get("hora"))

    linhas = [
        "🚌 <b>Circular UFRB — Principal</b>",
        "",
        "🔵 <b>Volta de referência atual</b>",
        f"🕐 Referência: <b>{atual['hora']}</b> — {origem}",
        f"🚪 Referência do Portão 1: <b>{previsao['inicio']}–{previsao['fim']}</b>",
        "ℹ️ A referência permanece até que os pontos indiquem uma nova volta ou o bloco termine.",
    ]

    if ultima_do_bloco:
        linhas.append("🏁 <b>Esta é a última volta deste bloco operacional.</b>")

    _adicionar_proximas(linhas, atual, 3)
    return "\n".join(linhas)
