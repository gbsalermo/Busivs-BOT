from datetime import datetime, timedelta

from blocos_operacionais import contexto_bloco_encerrado
from dados import HORARIOS
from regras import estado_vazio


TOLERANCIA_NOVA_VOLTA_MINUTOS = 5
MARCADOR_FIM_BLOCO = "operacao_encerrada_bloco"


def _horario_no_dia(hora, agora):
    hh, mm = map(int, hora.split(":"))
    return agora.replace(hour=hh, minute=mm, second=0, microsecond=0)


def _estado_bloco_encerrado(contexto):
    bloco = contexto["bloco"]
    estado = estado_vazio()
    estado["resultado_rota"] = {
        MARCADOR_FIM_BLOCO: True,
        "bloco_id": bloco["id"],
        "inicio_bloco": bloco["inicio"],
        "ultima_volta": bloco["ultima"],
        "fim_previsto": contexto["fim_previsto"].isoformat(),
        "fim_do_dia": contexto["fim_do_dia"],
        "proxima": contexto.get("proxima"),
    }
    return estado


def _tem_marcador_fim_bloco(estado):
    resultado = (estado or {}).get("resultado_rota") or {}
    return bool(resultado.get(MARCADOR_FIM_BLOCO))


def expirar_confirmacao_volta_anterior(estado, agora):
    """Mantém apenas confirmações compatíveis com o bloco operacional atual.

    O bloco termina quando sua última volta retorna plausivelmente à Garagem.
    Em horário de pico, uma confirmação recente pode estender brevemente esse
    fechamento. Quando um bloco novo começa, o estado anterior ainda recebe a
    tolerância geral de 5 min; uma confirmação posterior à nova saída passa a
    pertencer naturalmente ao novo bloco.
    """
    contexto = contexto_bloco_encerrado(estado, agora)
    if contexto:
        return _estado_bloco_encerrado(contexto)

    # O marcador só representa a lacuna entre blocos. Assim que começa a
    # próxima operação, ele deixa de ser válido.
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

    # Se uma nova saída oficial ocorreu depois da confirmação, preservamos o
    # estado anterior por até 5 min. Isso cobre atrasos de pico sem deixar uma
    # volta antiga contaminar indefinidamente o bloco novo. Uma confirmação
    # feita depois da nova saída não é apagada por esta regra.
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
