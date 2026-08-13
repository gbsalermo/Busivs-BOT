from blocos_operacionais import expiracao_aviso_do_bloco


def expiracao_bloco_aviso(agora):
    """Expira o aviso no fechamento do único bloco ao qual ele pertence.

    Avisos não atravessam blocos operacionais. Isso inclui o turno noturno:
    20:40, 21:40 e 22:30 são três blocos distintos, embora pertençam ao mesmo
    período da noite.
    """
    return expiracao_aviso_do_bloco(agora)
