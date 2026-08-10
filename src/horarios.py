"""Regras de horários e estimativas do Circular UFRB.

Este módulo lê ``data/horarios_letivo.json`` e transforma horários oficiais em
informações úteis para a interface: próxima saída, período do dia, previsão de
passagem no Portão 1, possíveis janelas de percurso e momentos de espera.

Importante: tudo que sai deste arquivo é baseado em horário previsto. Nenhuma
função daqui representa uma confirmação real de passagem. As confirmações dos
alunos são tratadas em ``passagens.py``.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Caminho absoluto evita problemas quando o programa é iniciado de diretórios
# diferentes.
CAMINHO_HORARIOS = Path(__file__).resolve().parent.parent / "data" / "horarios_letivo.json"

# O Campus Cruz das Almas utiliza horário de Brasília (UTC-3). Mantemos um fuso
# explícito porque o bot futuramente pode ser hospedado em servidor com outro
# timezone configurado no sistema operacional.
FUSO_LOCAL = timezone(timedelta(hours=-3))

# Depois da previsão final de chegada ao Portão 1, estes valores ajudam a criar
# uma janela aproximada em que o ônibus pode estar seguindo de volta para a
# origem/aguardando a próxima saída. São heurísticas, não GPS.
MARGEM_RETORNO_MINUTOS = 5
DURACAO_RETORNO_MINUTOS = 15

# Textos usados pela listagem por período no Telegram.
TITULOS_PERIODOS = {
    "manha": "🌅 <b>Horários da manhã</b>",
    "meio_dia": "🍽️ <b>Horários do almoço</b>",
    "tarde": "🌤️ <b>Horários da tarde</b>",
    "noite": "🌙 <b>Horários da noite</b>",
}

NOMES_PERIODOS = {
    "manha": "manhã",
    "meio_dia": "almoço",
    "tarde": "tarde",
    "noite": "noite",
}

# Faixas mostradas apenas como legenda para o usuário. A decisão de cada saída
# ser ou não pico é feita por ``_eh_horario_pico``.
FAIXAS_PICO_PERIODOS = {
    "manha": "07:40–08:20 e 11:30–12:45",
    "meio_dia": "11:30–14:00",
    "tarde": "13:00–14:00",
    "noite": "17:30–18:40",
}


def carregar_horarios() -> dict:
    """Lê e devolve todo o conteúdo do arquivo de horários letivos."""
    with CAMINHO_HORARIOS.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _minutos(horario: str) -> int:
    """Converte ``HH:MM`` para minutos desde 00:00.

    Exemplo: ``10:30`` vira ``630``. Trabalhar com um único número simplifica
    comparações, somas e criação de intervalos.
    """
    hora, minuto = map(int, horario.split(":"))
    return hora * 60 + minuto


def _formatar_minutos(total_minutos: int) -> str:
    """Converte minutos desde 00:00 novamente para ``HH:MM``.

    O módulo de 24 horas impede que valores acima de 1440 produzam horários
    inválidos em uma eventual soma que atravesse a meia-noite.
    """
    total_minutos %= 24 * 60
    hora = total_minutos // 60
    minuto = total_minutos % 60
    return f"{hora:02d}:{minuto:02d}"


def _nome_origem(origem: str) -> str:
    """Padroniza nomes de origem para textos curtos da interface."""
    origem_normalizada = origem.strip().lower()

    if "ru" in origem_normalizada:
        return "RU"
    if "garagem" in origem_normalizada:
        return "Garagem"

    return origem


def _icone_origem(origem: str) -> str:
    """Escolhe um ícone de acordo com a origem informada no horário."""
    origem_normalizada = origem.strip().lower()

    if "ru" in origem_normalizada:
        return "🍽️"
    if "garagem" in origem_normalizada:
        return "🅿️"
    if "portão 1" in origem_normalizada or "portao 1" in origem_normalizada:
        return "🚪"

    return "📍"


def _pertence_ao_periodo(hora: str, periodo: str) -> bool:
    """Informa se uma saída deve aparecer na listagem de determinado período.

    As faixas se sobrepõem propositalmente em alguns pontos. Por exemplo, saídas
    próximas ao almoço podem aparecer tanto na manhã quanto no bloco de almoço,
    facilitando a consulta conforme a forma como o aluno pensa no horário.
    """
    minutos = _minutos(hora)

    if periodo == "manha":
        return minutos <= _minutos("12:20")

    if periodo == "meio_dia":
        return _minutos("11:30") <= minutos <= _minutos("13:25")

    if periodo == "tarde":
        return _minutos("13:00") <= minutos < _minutos("17:30")

    if periodo == "noite":
        return minutos >= _minutos("17:30")

    return False


def _periodo_por_hora(agora: datetime) -> tuple[str, str]:
    """Retorna ícone e nome do período correspondente ao horário atual."""
    minutos = agora.hour * 60 + agora.minute

    if minutos < _minutos("11:30"):
        return "🌅", "Manhã"
    if minutos < _minutos("13:00"):
        return "🍽️", "Almoço"
    if minutos < _minutos("17:30"):
        return "🌤️", "Tarde"
    return "🌙", "Noite"


def _eh_horario_pico(hora: str) -> bool:
    """Classifica uma saída em uma das faixas consideradas de pico.

    Saídas de pico recebem uma previsão um pouco maior até o Portão 1. Os
    limites atuais são heurísticos e devem ser recalibrados após uso real.
    """
    minutos = _minutos(hora)

    return (
        _minutos("07:30") <= minutos <= _minutos("08:00")
        or _minutos("11:30") <= minutos <= _minutos("14:00")
        or _minutos("17:30") <= minutos <= _minutos("18:15")
    )


def estimar_chegada_portao_1(hora_saida: str) -> dict:
    """Estima a janela de passagem no Portão 1 a partir da hora de saída.

    Em horário normal são usados 15–20 minutos. Em horário de pico, 20–25.
    O retorno contém também flags usadas apenas para apresentação.

    Esta é uma referência aproximada de parte do percurso, não uma garantia de
    que o ônibus estará no Portão 1 naquele intervalo.
    """
    minutos_saida = _minutos(hora_saida)
    pico = _eh_horario_pico(hora_saida)

    minimo = 20 if pico else 15
    maximo = 25 if pico else 20

    return {
        "inicio": _formatar_minutos(minutos_saida + minimo),
        "fim": _formatar_minutos(minutos_saida + maximo),
        "pico": pico,
        "noturno": minutos_saida >= _minutos("20:00"),
    }


def _formatar_viagem(horario: dict) -> list[str]:
    """Formata uma saída e sua referência do Portão 1 para o Telegram."""
    hora = horario["hora"]
    origem = horario["origem"]
    nome_origem = _nome_origem(origem)
    previsao = estimar_chegada_portao_1(hora)

    alerta = " ⚠️ (horário de pico)" if previsao["pico"] else ""
    linhas = [
        f"🕒 <code>{hora}</code> · {nome_origem} → Rua{alerta}",
        f"🚪 Portão 1: <code>{previsao['inicio']}</code>–<code>{previsao['fim']}</code>",
    ]

    # No período noturno o trânsito pode permitir passagem antes da estimativa;
    # evitamos repetir esse aviso quando a própria saída já está marcada como pico.
    if previsao["noturno"] and not previsao["pico"]:
        linhas.append("🌙 <i>À noite pode chegar antes da estimativa.</i>")

    return linhas


def viagem_em_andamento(
    veiculo: str = "principal", agora: datetime | None = None
) -> dict | None:
    """Procura uma saída cuja janela até o Portão 1 ainda esteja aberta.

    Returns:
        O horário oficial mais recente compatível com a janela atual ou
        ``None``. Isto significa apenas "possivelmente em andamento".
    """
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])

    if not horarios:
        return None

    agora = agora or datetime.now(FUSO_LOCAL)
    minutos_agora = agora.hour * 60 + agora.minute

    candidatos = []
    for horario in horarios:
        minutos_saida = _minutos(horario["hora"])
        previsao = estimar_chegada_portao_1(horario["hora"])
        minutos_fim = _minutos(previsao["fim"])

        if minutos_saida <= minutos_agora <= minutos_fim:
            candidatos.append(horario)

    if not candidatos:
        return None

    # Se janelas se sobrepõem, a saída oficial mais recente é a melhor referência.
    return max(candidatos, key=lambda horario: _minutos(horario["hora"]))


def proximo_horario(
    veiculo: str = "principal", agora: datetime | None = None
) -> dict | None:
    """Retorna a primeira saída oficial estritamente posterior ao minuto atual."""
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])

    if not horarios:
        return None

    agora = agora or datetime.now(FUSO_LOCAL)
    minutos_agora = agora.hour * 60 + agora.minute

    for horario in horarios:
        if _minutos(horario["hora"]) > minutos_agora:
            return horario

    return None


def viagem_em_retorno(
    veiculo: str = "principal", agora: datetime | None = None
) -> dict | None:
    """Estima se o ônibus pode estar no trecho posterior ao Portão 1.

    A janela começa alguns minutos depois do fim da previsão do Portão 1 e dura
    no máximo ``DURACAO_RETORNO_MINUTOS``. Ela nunca ultrapassa a próxima saída
    oficial, evitando sobrepor estados incompatíveis.
    """
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])

    if not horarios:
        return None

    agora = agora or datetime.now(FUSO_LOCAL)
    minutos_agora = agora.hour * 60 + agora.minute

    for indice, horario in enumerate(horarios):
        previsao = estimar_chegada_portao_1(horario["hora"])
        inicio_retorno = _minutos(previsao["fim"]) + MARGEM_RETORNO_MINUTOS
        proxima_saida = (
            _minutos(horarios[indice + 1]["hora"])
            if indice + 1 < len(horarios)
            else 24 * 60
        )
        fim_retorno = min(inicio_retorno + DURACAO_RETORNO_MINUTOS, proxima_saida)

        if inicio_retorno <= minutos_agora < fim_retorno:
            return {
                "viagem": horario,
                "origem": _nome_origem(horario["origem"]),
                "inicio_retorno": _formatar_minutos(inicio_retorno),
                "fim_retorno": _formatar_minutos(fim_retorno),
                "proxima": horarios[indice + 1] if indice + 1 < len(horarios) else None,
            }

    return None


def aguardando_proxima_saida(
    veiculo: str = "principal", agora: datetime | None = None
) -> dict | None:
    """Detecta a janela em que uma volta terminou e a próxima ainda não saiu.

    Essa informação é usada tanto para mensagens de provável espera quanto para
    impedir confirmações colaborativas claramente fora de circulação.
    """
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])

    if not horarios:
        return None

    agora = agora or datetime.now(FUSO_LOCAL)
    minutos_agora = agora.hour * 60 + agora.minute

    for indice, horario in enumerate(horarios[:-1]):
        previsao = estimar_chegada_portao_1(horario["hora"])
        inicio_retorno = _minutos(previsao["fim"]) + MARGEM_RETORNO_MINUTOS
        fim_retorno = inicio_retorno + DURACAO_RETORNO_MINUTOS
        proxima = horarios[indice + 1]
        proxima_saida = _minutos(proxima["hora"])

        if fim_retorno <= minutos_agora < proxima_saida:
            return {
                "origem": _nome_origem(horario["origem"]),
                "proxima": proxima,
            }

    return None


def montar_resumo_horarios(
    veiculo: str = "principal", agora: datetime | None = None
) -> str:
    """Monta a tela de 'Próximos horários'.

    Exibe a próxima saída em destaque e até três horários seguintes, sempre com
    a previsão do Portão 1. Também trata fim de semana, ausência de cadastro e
    encerramento das viagens do dia.
    """
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])
    nome = "Principal" if veiculo == "principal" else "Micro"

    if not horarios:
        return f"⏰ <b>{nome}</b>\n\nOs horários ainda não foram cadastrados no sistema."

    agora = agora or datetime.now(FUSO_LOCAL)
    primeiro = horarios[0]
    ultimo = horarios[-1]

    if agora.weekday() >= 5:
        return (
            f"🚌 <b>Circular UFRB — {nome}</b>\n\n"
            "O Circular opera de segunda a sexta-feira.\n\n"
            f"🕐 <b>Primeiro horário:</b> <code>{primeiro['hora']}</code>\n"
            f"🌙 <b>Último horário:</b> <code>{ultimo['hora']}</code>"
        )

    proximo = proximo_horario(veiculo, agora)

    if proximo is None:
        return (
            f"🚌 <b>Circular UFRB — {nome}</b>\n\n"
            "As viagens de hoje já encerraram.\n\n"
            f"🕐 <b>Primeiro horário:</b> <code>{primeiro['hora']}</code>\n"
            f"🌙 <b>Último horário:</b> <code>{ultimo['hora']}</code>"
        )

    icone_periodo, nome_periodo = _periodo_por_hora(agora)
    indice = horarios.index(proximo)

    # Mostramos no máximo três saídas depois da próxima para manter a tela curta.
    seguintes = horarios[indice + 1:indice + 4]

    linhas = [
        f"🚌 <b>Circular UFRB — {nome}</b>",
        f"{icone_periodo} <b>{nome_periodo}</b>",
        "",
        "🟢 <b>Próxima saída</b>",
    ]
    linhas.extend(_formatar_viagem(proximo))

    if seguintes:
        linhas.extend(["", "📋 <b>Próximos horários</b>"])
        for horario in seguintes:
            previsao = estimar_chegada_portao_1(horario["hora"])
            alerta = " ⚠️ (horário de pico)" if previsao["pico"] else ""
            linhas.extend(
                [
                    f"<code>{horario['hora']}</code> · {_nome_origem(horario['origem'])} → Rua{alerta}",
                    f"🚪 Portão 1: <code>{previsao['inicio']}</code>–<code>{previsao['fim']}</code>",
                ]
            )

    linhas.extend(
        [
            "",
            "ℹ️ <i>Os horários do Portão 1 são previsões e podem variar com trânsito, lotação e atrasos.</i>",
        ]
    )

    return "\n".join(linhas)


def _proxima_saida_do_periodo(
    horarios_periodo: list[dict], agora: datetime
) -> dict | None:
    """Encontra a primeira saída do período que ainda não passou."""
    minutos_agora = agora.hour * 60 + agora.minute

    for horario in horarios_periodo:
        if _minutos(horario["hora"]) >= minutos_agora:
            return horario

    return None


def _formatar_saida_compacta(horario: dict) -> str:
    """Formata uma linha compacta usada na listagem completa por período."""
    hora = horario["hora"]
    origem = _nome_origem(horario["origem"])
    previsao = estimar_chegada_portao_1(hora)
    alerta = " ⚠️ (horário de pico)" if previsao["pico"] else ""

    return (
        f"<code>{hora}</code> · {origem}  "
        f"🚪 <code>{previsao['inicio']}</code>–<code>{previsao['fim']}</code>{alerta}"
    )


def listar_horarios_periodo(periodo: str, veiculo: str = "principal") -> str:
    """Monta a listagem completa de horários para manhã, almoço, tarde ou noite.

    Além das saídas do período, destaca a próxima disponível e explica que o
    Portão 1 é apenas uma referência estimada. Horários de pico recebem marcação
    explícita para facilitar a leitura.
    """
    dados = carregar_horarios()
    horarios = dados.get(veiculo, [])
    nome = "Principal" if veiculo == "principal" else "Micro"

    horarios_periodo = [
        horario for horario in horarios if _pertence_ao_periodo(horario["hora"], periodo)
    ]

    if not horarios_periodo:
        return f"📋 <b>{nome}</b>\n\nNenhum horário cadastrado para este período."

    agora = datetime.now(FUSO_LOCAL)
    proxima = _proxima_saida_do_periodo(horarios_periodo, agora)
    nome_periodo = NOMES_PERIODOS.get(periodo, "período")

    linhas = [
        f"🚌 <b>Circular UFRB — {nome}</b>",
        TITULOS_PERIODOS.get(periodo, periodo.title()),
        "",
        "➡️ <b>SENTIDO: RUA</b>",
        "🚪 Referência: passagem no Portão 1",
    ]

    if proxima is not None:
        previsao_proxima = estimar_chegada_portao_1(proxima["hora"])
        alerta_proxima = " ⚠️ (horário de pico)" if previsao_proxima["pico"] else ""
        linhas.extend(
            [
                "",
                "🟢 <b>PRÓXIMO ÔNIBUS</b>",
                f"<code>{proxima['hora']}</code> · saída do {_nome_origem(proxima['origem'])}{alerta_proxima}",
                f"🚪 Portão 1: <code>{previsao_proxima['inicio']}</code>–<code>{previsao_proxima['fim']}</code>",
            ]
        )
    else:
        linhas.extend(
            [
                "",
                "✅ Não há mais saídas previstas para este período hoje.",
            ]
        )

    linhas.extend(["", f"📋 <b>Saídas do {nome_periodo}</b>"])

    for horario in horarios_periodo:
        linhas.append(_formatar_saida_compacta(horario))

    # A legenda de pico só aparece quando ao menos uma saída da lista recebe a
    # classificação de pico.
    if any(estimar_chegada_portao_1(horario["hora"])["pico"] for horario in horarios_periodo):
        faixa_pico = FAIXAS_PICO_PERIODOS.get(periodo)
        linhas.extend(
            [
                "",
                f"⚠️ <b>Horário de pico:</b> {faixa_pico}" if faixa_pico else "⚠️ <b>Há horários de pico neste período.</b>",
                "Pode haver pequenos atrasos.",
            ]
        )
    else:
        linhas.extend(
            [
                "",
                "ℹ️ Horários do Portão 1 são previsões e podem variar.",
            ]
        )

    return "\n".join(linhas)
