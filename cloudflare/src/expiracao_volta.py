from datetime import datetime, timedelta

from dados import HORARIOS
from regras import estado_vazio, estimar_chegada_portao_1


TOLERANCIA_NOVA_VOLTA_MINUTOS = 5
TOLERANCIA_FIM_BLOCO_DIA_MINUTOS = 15
TOLERANCIA_FIM_BLOCO_NOITE_MINUTOS = 10
MARCADOR_FIM_BLOCO = "operacao_encerrada_bloco"


def _horario_no_dia(hora, agora):
    hh, mm = map(int, hora.split(":"))
    return agora.replace(hour=hh, minute=mm, second=0, microsecond=0)


def _origem_garagem(viagem):
    return "garagem" in str((viagem or {}).get("origem", "")).strip().lower()


def _fim_previsto_volta(viagem, agora):
    previsao = estimar_chegada_portao_1(viagem["hora"])
    fim_portao_1 = _horario_no_dia(previsao["fim"], agora)
    tolerancia = (
        TOLERANCIA_FIM_BLOCO_NOITE_MINUTOS
        if previsao.get("noturno")
        else TOLERANCIA_FIM_BLOCO_DIA_MINUTOS
    )
    return fim_portao_1 + timedelta(minutes=tolerancia)


def contexto_bloco_encerrado(agora):
    """Retorna o intervalo em que a ultima volta de um bloco ja terminou.

    Uma volta e considerada a ultima do bloco quando a proxima saida oficial
    parte da Garagem, ou quando ela e a ultima viagem cadastrada do dia.

    O encerramento ocorre apos a previsao maxima do Portao 1 mais uma pequena
    tolerancia de retorno: 15 min durante o dia e 10 min a noite.
    """
    horarios = HORARIOS["principal"]

    for i, viagem in enumerate(horarios):
        proxima = horarios[i + 1] if i + 1 < len(horarios) else None
        ultima_do_bloco = proxima is None or _origem_garagem(proxima)
        if not ultima_do_bloco:
            continue

        fim_previsto = _fim_previsto_volta(viagem, agora)
        proxima_saida = _horario_no_dia(proxima["hora"], agora) if proxima else None

        # Quando a proxima saida acontece antes (ou exatamente no momento) do
        # fim estimado, nao existe uma janela intermediaria de bloco encerrado.
        if proxima_saida is not None and fim_previsto >= proxima_saida:
            continue

        if agora >= fim_previsto and (proxima_saida is None or agora < proxima_saida):
            return {
                "viagem": viagem,
                "fim_previsto": fim_previsto,
                "proxima": proxima,
                "fim_do_dia": proxima is None,
            }

    return None


def _estado_bloco_encerrado(contexto):
    estado = estado_vazio()
    estado["resultado_rota"] = {
        MARCADOR_FIM_BLOCO: True,
        "ultima_volta": contexto["viagem"]["hora"],
        "fim_previsto": contexto["fim_previsto"].isoformat(),
        "fim_do_dia": contexto["fim_do_dia"],
        "proxima": contexto.get("proxima"),
    }
    return estado


def _tem_marcador_fim_bloco(estado):
    resultado = (estado or {}).get("resultado_rota") or {}
    return bool(resultado.get(MARCADOR_FIM_BLOCO))


def expirar_confirmacao_volta_anterior(estado, agora):
    """Descarta confirmacoes que ja nao representam uma volta ativa.

    Alem da regra de nova saida + 5 min, encerra explicitamente a ultima volta
    de cada bloco quando termina a janela plausivel de retorno. Isso evita que
    a ultima viagem do dia (ou de um bloco) permaneça ativa indefinidamente.
    """
    contexto = contexto_bloco_encerrado(agora)
    if contexto:
        return _estado_bloco_encerrado(contexto)

    # Um marcador de bloco encerrado so vale durante a lacuna ate a proxima
    # saida. Quando a operacao recomeca, ele deve desaparecer.
    if _tem_marcador_fim_bloco(estado):
        return estado_vazio()

    horario_estado = estado.get("horario")
    if not horario_estado:
        return estado

    try:
        confirmado_em = datetime.fromisoformat(horario_estado)
    except (TypeError, ValueError):
        return estado

    if confirmado_em.date() != agora.date():
        return estado_vazio()

    # Procuramos a saida oficial mais recente que aconteceu depois da ultima
    # confirmacao. Se a tolerancia dessa saida ja acabou, o estado e antigo.
    saidas_posteriores = []
    for viagem in HORARIOS["principal"]:
        saida = _horario_no_dia(viagem["hora"], agora)
        if confirmado_em < saida <= agora:
            saidas_posteriores.append(saida)

    if not saidas_posteriores:
        return estado

    ultima_saida = max(saidas_posteriores)
    fim_tolerancia = ultima_saida + timedelta(minutes=TOLERANCIA_NOVA_VOLTA_MINUTOS)

    if agora >= fim_tolerancia:
        return estado_vazio()

    return estado
