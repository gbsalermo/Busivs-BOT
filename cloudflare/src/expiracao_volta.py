from datetime import datetime

from blocos_operacionais import contexto_bloco_encerrado
from regras import estado_vazio

MARCADOR_FIM_BLOCO = "operacao_encerrada_bloco"


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
    """Horários internos são referência, não gatilho de troca de volta.

    Uma confirmação permanece ligada à volta corrente mesmo que o relógio passe
    por outra saída oficial. A troca de volta é inferida pelas novas evidências
    de pontos. O horário volta a ser regra apenas no fechamento efetivo do bloco
    e na abertura da operação seguinte.
    """
    contexto = contexto_bloco_encerrado(estado, agora)
    if contexto:
        return _estado_bloco_encerrado(contexto)

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

    return estado
