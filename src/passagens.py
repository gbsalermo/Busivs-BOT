"""Estado colaborativo e resposta de localização do BUSIVS BOT.

Este módulo é o centro da lógica de "Onde está o ônibus?". Ele combina três
fontes de informação:

1. confirmações reais enviadas pelos alunos;
2. sequência conhecida da rota;
3. horários oficiais usados apenas como referência/estimativa.

O estado é propositalmente mantido em memória. O objetivo atual não é guardar
histórico permanente, e sim representar o contexto operacional do ônibus agora.
As confirmações expiram naturalmente entre blocos operacionais ou na mudança de
dia.

Princípio importante: confirmação real e estimativa nunca devem ser tratadas
como a mesma coisa. Uma confirmação recente tem prioridade sobre inferências de
horário, e horários são usados apenas para preencher contexto quando faltam
dados colaborativos.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from horarios import aguardando_proxima_saida, proximo_horario, viagem_em_andamento, viagem_em_retorno
from rota import carregar_pontos, carregar_rota

# Fuso usado em todos os horários registrados em memória.
FUSO_LOCAL = timezone(timedelta(hours=-3))
CAMINHO_HORARIOS = Path(__file__).resolve().parent.parent / "data" / "horarios_letivo.json"

# Janela em que uma saída oficial passada ainda pode servir de contexto para um
# ônibus atrasado. Não significa que o ônibus realmente esteja circulando.
JANELA_SAIDA_RECENTE_MINUTOS = 45

# Antes de uma saída programada da Garagem, o bot pode informar que o veículo
# provavelmente está aguardando lá.
JANELA_PRE_SAIDA_GARAGEM_MINUTOS = 5

# Confirmações com até 30 minutos são consideradas recentes em regras de
# proteção contra falsos registros durante possíveis atrasos.
JANELA_CONFIRMACAO_RECENTE_MINUTOS = 30

# Saídas separadas por mais de 60 minutos iniciam um novo bloco operacional.
LIMITE_INTERVALO_BLOCO_MINUTOS = 60

# Histórico curto usado apenas para corrigir/inferir sequências colaborativas.
MAX_HISTORICO_REGISTROS = 20

# Estado corrente do ônibus. Esse dicionário é compartilhado pelo processo e é
# resetado quando o contexto operacional expira.
_estado = {
    "ponto_anterior": None,
    "ponto_atual": None,
    "horario": None,
    "telegram_id": None,
    "resultado_rota": None,
}

# Evidências recentes de passagem. Diferente de um banco de dados, este
# histórico existe apenas durante a execução/bloco atual.
_historico_passagens = []


def limpar_estado() -> None:
    """Apaga localização atual e histórico colaborativo em memória.

    É usado na troca de bloco operacional, mudança de dia e em testes. O bot
    continua rodando; apenas o contexto antigo do ônibus é descartado.
    """
    _estado.update(
        {
            "ponto_anterior": None,
            "ponto_atual": None,
            "horario": None,
            "telegram_id": None,
            "resultado_rota": None,
        }
    )
    _historico_passagens.clear()


def obter_estado() -> dict:
    """Retorna uma cópia rasa do estado atual para leitura/testes."""
    return _estado.copy()


def obter_historico() -> list[dict]:
    """Retorna cópias dos registros recentes sem expor a lista interna."""
    return [registro.copy() for registro in _historico_passagens]


def _nome_ponto(ponto_id: str) -> str:
    """Converte um ID de ponto para o nome amigável cadastrado no JSON."""
    pontos = carregar_pontos()
    ponto = pontos.get(ponto_id)
    return ponto["nome"] if ponto else ponto_id


def _ocorrencias(rota: list[dict], ponto_id: str) -> list[int]:
    """Retorna todos os índices em que um ponto aparece na rota.

    Isso é necessário porque RU e Biblioteca aparecem mais de uma vez.
    """
    return [
        indice
        for indice, item in enumerate(rota)
        if item["ponto_id"] == ponto_id
    ]


def _proximo_da_ocorrencia(
    rota: list[dict], indice_atual: int, pontos: dict[str, dict]
) -> dict | None:
    """Monta o próximo ponto esperado a partir de uma ocorrência da rota.

    Quando o próximo ponto é opcional, também procura a próxima alternativa
    obrigatória. Assim o Telegram pode informar o que acontece caso o ônibus
    não pare no ponto opcional.
    """
    if indice_atual + 1 >= len(rota):
        return None

    item_proximo = rota[indice_atual + 1]
    ponto_proximo = pontos[item_proximo["ponto_id"]]
    proximo = {
        "id": ponto_proximo["id"],
        "nome": ponto_proximo["nome"],
        "opcional": item_proximo.get("opcional", ponto_proximo.get("opcional", False)),
    }

    if proximo["opcional"]:
        indice_alternativo = indice_atual + 2
        while indice_alternativo < len(rota):
            item_alternativo = rota[indice_alternativo]
            if not item_alternativo.get("opcional", False):
                ponto_alternativo = pontos[item_alternativo["ponto_id"]]
                proximo["alternativa"] = {
                    "id": ponto_alternativo["id"],
                    "nome": ponto_alternativo["nome"],
                }
                break
            indice_alternativo += 1

    return proximo


def _analisar_registros_esparsos(
    ponto_anterior: str, ponto_atual: str
) -> dict | None:
    """Tenta encaixar duas confirmações em qualquer trecho crescente da rota.

    Diferente de ``rota.analisar_trecho``, aqui os pontos não precisam ser
    imediatamente consecutivos. Isso é importante em um sistema colaborativo:
    nem todo ponto receberá uma confirmação.

    Quando há mais de uma combinação possível, escolhemos a menor distância na
    rota, isto é, a explicação mais curta compatível com os dois registros.
    """
    rota = carregar_rota()
    pontos = carregar_pontos()

    if ponto_anterior not in pontos or ponto_atual not in pontos:
        return None

    anteriores = _ocorrencias(rota, ponto_anterior)
    atuais = _ocorrencias(rota, ponto_atual)

    candidatos = []
    for indice_anterior in anteriores:
        for indice_atual in atuais:
            if indice_atual > indice_anterior:
                candidatos.append((indice_atual - indice_anterior, indice_atual))

    if not candidatos:
        return None

    _, indice_atual = min(candidatos, key=lambda item: item[0])
    item_atual = rota[indice_atual]

    return {
        "ponto_anterior": pontos[ponto_anterior]["nome"],
        "ponto_atual": pontos[ponto_atual]["nome"],
        "ponto_atual_id": ponto_atual,
        "indice_atual": indice_atual,
        "sentido": item_atual["sentido_apos"],
        "proximo": _proximo_da_ocorrencia(rota, indice_atual, pontos),
    }


def _registrar_no_historico(
    ponto_id: str, horario: datetime, telegram_id: int | None
) -> None:
    """Adiciona uma evidência ao histórico curto de confirmações.

    O limite impede crescimento indefinido da memória. Quando excedido, os
    registros mais antigos são descartados primeiro.
    """
    _historico_passagens.append(
        {
            "ponto_id": ponto_id,
            "horario": horario,
            "telegram_id": telegram_id,
        }
    )

    if len(_historico_passagens) > MAX_HISTORICO_REGISTROS:
        del _historico_passagens[:-MAX_HISTORICO_REGISTROS]


def _resultado_com_historico(ponto_atual: str) -> dict | None:
    """Busca no histórico a melhor confirmação anterior para o ponto atual.

    A busca começa do registro mais recente e recua até encontrar uma sequência
    compatível. Isso permite ignorar uma confirmação equivocada sem bloquear as
    confirmações corretas que vêm depois.
    """
    total = len(_historico_passagens)

    for indice in range(total - 1, -1, -1):
        registro = _historico_passagens[indice]
        ponto_anterior = registro["ponto_id"]

        # Repetir o mesmo ponto não ajuda a inferir deslocamento.
        if ponto_anterior == ponto_atual:
            continue

        resultado = _analisar_registros_esparsos(ponto_anterior, ponto_atual)
        if resultado is None:
            continue

        resultado["base_historico"] = {
            "ponto_id": ponto_anterior,
            "horario": registro["horario"],
            "telegram_id": registro["telegram_id"],
        }
        resultado["ignorou_registro_incompativel"] = indice != total - 1
        return resultado

    return None


def _carregar_horarios_principal() -> list[dict]:
    """Carrega apenas as saídas cadastradas para o ônibus Principal."""
    with CAMINHO_HORARIOS.open("r", encoding="utf-8") as arquivo:
        horarios = json.load(arquivo)

    return horarios.get("principal", [])


def _minutos_horario(hora_texto: str) -> int:
    """Converte ``HH:MM`` para minutos desde o início do dia."""
    hora, minuto = map(int, hora_texto.split(":"))
    return hora * 60 + minuto


def _horario_previsto_hoje(hora_texto: str, agora: datetime) -> datetime:
    """Transforma um ``HH:MM`` oficial em ``datetime`` no dia de ``agora``."""
    hora, minuto = map(int, hora_texto.split(":"))
    return agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)


def _quebra_de_bloco_mais_recente(agora: datetime) -> datetime | None:
    """Localiza o início do bloco operacional mais recente já alcançado.

    Duas saídas separadas por mais de ``LIMITE_INTERVALO_BLOCO_MINUTOS`` marcam
    uma quebra. O horário da saída seguinte é considerado o início do novo
    bloco.
    """
    horarios = _carregar_horarios_principal()
    quebra_mais_recente = None

    for anterior, proxima in zip(horarios, horarios[1:]):
        intervalo = _minutos_horario(proxima["hora"]) - _minutos_horario(anterior["hora"])
        if intervalo <= LIMITE_INTERVALO_BLOCO_MINUTOS:
            continue

        inicio_novo_bloco = _horario_previsto_hoje(proxima["hora"], agora)
        if inicio_novo_bloco <= agora:
            quebra_mais_recente = inicio_novo_bloco

    return quebra_mais_recente


def _aguardando_em_lacuna_de_bloco(agora: datetime) -> bool:
    """Verifica se a espera atual está dentro de uma quebra real de bloco.

    Nem toda espera entre duas saídas encerra o contexto. Apenas lacunas acima
    do limite de 60 minutos devem invalidar uma localização antiga.
    """
    aguardando = aguardando_proxima_saida("principal", agora)
    if aguardando is None or aguardando.get("proxima") is None:
        return False

    horarios = _carregar_horarios_principal()
    proxima_hora = aguardando["proxima"]["hora"]

    for indice, horario in enumerate(horarios):
        if horario["hora"] != proxima_hora or indice == 0:
            continue

        anterior = horarios[indice - 1]
        intervalo = _minutos_horario(proxima_hora) - _minutos_horario(anterior["hora"])
        return intervalo > LIMITE_INTERVALO_BLOCO_MINUTOS

    return False


def _ultima_saida_oficial_recente(agora: datetime) -> dict | None:
    """Retorna a última saída oficial ocorrida nos últimos 45 minutos.

    A origem pode ser Garagem ou RU. A função existe para dar contexto a uma
    primeira confirmação quando uma volta pode estar atrasada. Ela não confirma
    que a saída realmente aconteceu no horário.
    """
    candidatos = []

    for viagem in _carregar_horarios_principal():
        previsto = _horario_previsto_hoje(viagem["hora"], agora)
        diferenca = agora - previsto

        if timedelta(0) <= diferenca <= timedelta(minutes=JANELA_SAIDA_RECENTE_MINUTOS):
            candidatos.append((previsto, viagem))

    if not candidatos:
        return None

    previsto, viagem = max(candidatos, key=lambda item: item[0])
    return {
        "hora": viagem["hora"],
        "origem": viagem["origem"],
        "previsto": previsto,
    }


def _proxima_saida_garagem_em_breve(agora: datetime) -> dict | None:
    """Detecta uma saída da Garagem prevista para os próximos cinco minutos.

    É usada somente quando não existe localização confirmada, permitindo
    responder que o ônibus provavelmente está na Garagem prestes a sair.
    """
    proxima = proximo_horario("principal", agora)
    if proxima is None or proxima.get("origem") != "Garagem":
        return None

    previsto = _horario_previsto_hoje(proxima["hora"], agora)
    diferenca = previsto - agora

    if not timedelta(0) < diferenca <= timedelta(minutes=JANELA_PRE_SAIDA_GARAGEM_MINUTOS):
        return None

    return {
        "hora": proxima["hora"],
        "origem": proxima["origem"],
        "previsto": previsto,
    }


def _estimar_primeiro_registro_por_horario(
    ponto_id: str, agora: datetime
) -> dict | None:
    """Usa uma saída oficial recente para contextualizar a primeira confirmação.

    Sem uma confirmação anterior não é possível deduzir o sentido apenas pela
    rota. Nesta situação, uma saída recente fornece uma hipótese de sentido RUA
    e permite indicar o próximo ponto esperado. A mensagem deixa explícito que
    o horário é apenas referência.
    """
    saida = _ultima_saida_oficial_recente(agora)
    if saida is None:
        return None

    rota = carregar_rota()
    pontos = carregar_pontos()

    ocorrencias = _ocorrencias(rota, ponto_id)
    if not ocorrencias:
        return None

    indice_atual = None
    for indice in ocorrencias:
        if rota[indice]["sentido_apos"] == "RUA":
            indice_atual = indice
            break

    if indice_atual is None:
        return None

    return {
        "horario_saida": saida["hora"],
        "origem_saida": saida["origem"],
        "sentido": "RUA",
        "proximo": _proximo_da_ocorrencia(rota, indice_atual, pontos),
    }


def _tempo_desde_confirmacao(
    horario: datetime | None, agora: datetime | None = None
) -> str:
    """Formata a idade de uma confirmação em linguagem amigável."""
    if horario is None:
        return "horário desconhecido"

    agora = agora or datetime.now(FUSO_LOCAL)
    segundos = max(0, int((agora - horario).total_seconds()))

    if segundos < 60:
        return "agora mesmo"

    minutos = segundos // 60
    if minutos < 60:
        return f"há {minutos} min"

    horas = minutos // 60
    minutos_restantes = minutos % 60

    if minutos_restantes == 0:
        return f"há {horas}h"

    return f"há {horas}h {minutos_restantes}min"


def _tem_confirmacao_recente(agora: datetime) -> bool:
    """Informa se o estado atual foi confirmado nos últimos 30 minutos."""
    horario = _estado["horario"]
    if horario is None:
        return False

    diferenca = agora - horario
    return timedelta(0) <= diferenca <= timedelta(minutes=JANELA_CONFIRMACAO_RECENTE_MINUTOS)


def _estado_expirou(agora: datetime) -> bool:
    """Decide se a localização em memória pertence a um contexto antigo.

    O estado expira quando:
    - pertence a outro dia;
    - ficou antes do início do bloco operacional atual;
    - estamos numa longa lacuna entre blocos e não há confirmação recente.

    Uma simples mudança de saída dentro do mesmo bloco não apaga o contexto.
    """
    horario = _estado["horario"]
    if horario is None:
        return False

    if horario.date() != agora.date():
        return True

    quebra_recente = _quebra_de_bloco_mais_recente(agora)
    if quebra_recente is not None and horario < quebra_recente:
        return True

    if _aguardando_em_lacuna_de_bloco(agora) and not _tem_confirmacao_recente(agora):
        return True

    return False


def _limpar_estado_se_expirado(agora: datetime) -> None:
    """Limpa o estado somente quando ``_estado_expirou`` indicar necessidade."""
    if _estado_expirou(agora):
        limpar_estado()


def _formatar_movimento(resultado: dict) -> str:
    """Transforma uma inferência de rota em texto para o usuário."""
    sentido = resultado.get("sentido")
    proximo = resultado.get("proximo")
    seta = "➡️" if sentido == "RUA" else "⬅️"

    linhas = []

    if proximo is None:
        # O RU é simultaneamente início e fim da rota. Ao chegar nele no fim da
        # sequência não é seguro afirmar o sentido da próxima volta.
        if resultado.get("ponto_atual_id") == "ru":
            linhas.extend(
                [
                    "🏁 Chegada ao RU / fim da volta confirmada.",
                    "🚌 O ônibus pode estar concluindo a volta anterior ou aguardando/iniciando uma nova saída.",
                    "ℹ️ Não é possível afirmar o sentido apenas por esta confirmação; os horários podem sofrer atraso.",
                ]
            )
            return "\n".join(linhas)

        linhas.append("🏁 Fim do percurso cadastrado.")
        linhas.append(f"{seta} Sentido: {sentido}")
        return "\n".join(linhas)

    if proximo["opcional"]:
        linhas.extend(
            [
                "⏭️ Próximo:",
                f"     📍 {proximo['nome']} (se houver parada)",
            ]
        )
        alternativa = proximo.get("alternativa")
        if alternativa:
            linhas.append(f"     ↪️ Caso não pare: {alternativa['nome']}")
    else:
        linhas.extend(
            [
                "⏭️ Próximo:",
                f"     📍 {proximo['nome']}",
            ]
        )

    linhas.append(f"{seta} Sentido: {sentido}")
    return "\n".join(linhas)


def _formatar_retorno(retorno: dict, proxima: dict | None) -> str:
    """Formata uma janela estimada posterior à passagem no Portão 1."""
    linhas = [
        "↩️ Percurso de retorno",
        "🚌 Pelo horário, o ônibus provavelmente está no percurso de retorno.",
        f"⬅️ Sentido: {retorno['origem']}",
        "📍 O ônibus ainda segue atendendo pontos durante esse percurso.",
    ]

    if proxima is not None:
        linhas.extend(
            [
                "",
                "⏰ Próxima volta prevista:",
                f"     🕐 {proxima['hora']} — {proxima['origem']}",
            ]
        )

    linhas.append("ℹ️ Situação estimada pelo horário, não por confirmação de passagem.")
    return "\n".join(linhas)


def _formatar_aguardando_saida(aguardando: dict) -> str:
    """Formata a situação estimada entre o fim de uma volta e a próxima saída."""
    proxima = aguardando.get("proxima")
    origem = aguardando["origem"]

    linhas = [
        f"🅿️ Provavelmente na {origem}" if origem == "Garagem" else f"📍 Provavelmente no {origem}",
        "🚌 Pelo horário, o ônibus provavelmente já concluiu o percurso anterior.",
    ]

    if proxima is not None:
        linhas.extend(
            [
                "",
                "⏰ Próxima saída prevista:",
                f"     🕐 {proxima['hora']} — {proxima['origem']}",
            ]
        )

    linhas.append("ℹ️ Situação estimada pelo horário, sem confirmação recente de passagem.")
    return "\n".join(linhas)


def _formatar_viagem_sem_confirmacao(viagem: dict) -> str:
    """Formata uma viagem prevista em andamento sem confirmação colaborativa."""
    return (
        "🚌 Há uma volta prevista em andamento.\n"
        f"🕐 Saída oficial: {viagem['hora']} — {viagem['origem']}\n"
        "➡️ Sentido provável: RUA\n\n"
        "ℹ️ Não há confirmação recente de passagem; o ônibus pode estar adiantado ou atrasado."
    )


def _formatar_saida_recente_sem_confirmacao(saida: dict) -> str:
    """Explica que uma saída recente ainda pode estar atrasada/em percurso."""
    return (
        "🚌 Uma saída oficial recente ainda pode estar em percurso por causa de atraso.\n"
        f"🕐 Saída prevista: {saida['hora']} — {saida['origem']}\n"
        "➡️ O sentido e a posição exata dependem de uma confirmação de passagem.\n\n"
        "ℹ️ O horário oficial é apenas referência; a volta pode estar atrasada."
    )


def _formatar_pre_saida_garagem(saida: dict) -> str:
    """Formata a previsão específica dos cinco minutos antes de sair da Garagem."""
    return (
        "🅿️ Sem confirmação recente, o ônibus provavelmente está na Garagem.\n\n"
        "⏰ Próxima saída prevista:\n"
        f"     🕐 {saida['hora']} — Garagem\n\n"
        "ℹ️ É uma previsão pelo horário oficial; pode haver atraso na chegada à garagem ou na saída."
    )


def _confirmacao_anterior_ao_retorno(
    horario: datetime | None, retorno: dict | None
) -> bool:
    """Verifica se uma confirmação ocorreu antes da janela estimada de retorno."""
    if horario is None or retorno is None:
        return False

    hora, minuto = map(int, retorno["inicio_retorno"].split(":"))
    inicio_retorno = horario.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    return horario < inicio_retorno


def _possivel_atraso_portao_1(
    ponto_id: str,
    horario_confirmacao: datetime | None,
    resultado_rota: dict | None,
) -> bool:
    """Aplica a regra experimental de atraso estudada para a saída das 10h.

    Hoje a regra é propositalmente estreita: entre 10:15 e 10:20, uma
    confirmação na Biblioteca/Pavilhão II ainda no sentido RUA pode indicar que
    a passagem prevista no Portão 1 está atrasada. Não generalizar sem dados de
    uso real.
    """
    if horario_confirmacao is None:
        return False

    if ponto_id not in {"biblioteca", "pavilhao_2"}:
        return False

    if resultado_rota is not None and resultado_rota.get("sentido") != "RUA":
        return False

    inicio = horario_confirmacao.replace(hour=10, minute=15, second=0, microsecond=0)
    fim = horario_confirmacao.replace(hour=10, minute=20, second=59, microsecond=999999)

    return inicio <= horario_confirmacao <= fim


def registrar_passagem(ponto_id: str, telegram_id: int | None = None) -> dict:
    """Registra uma confirmação colaborativa de passagem.

    Fluxo:
    1. valida se o ponto existe;
    2. descarta estado de bloco antigo;
    3. bloqueia registros em espera fora de circulação quando não há evidência
       recente de atraso;
    4. ignora duplicata do ponto atual;
    5. tenta inferir movimento usando o histórico recente;
    6. atualiza o estado para a confirmação mais nova;
    7. adiciona a evidência ao histórico curto.

    A confirmação mais recente vira o ponto atual mesmo quando ainda não há
    informação suficiente para inferir sentido. Isso evita que um registro
    anterior incorreto impeça o sistema de se corrigir.
    """
    pontos = carregar_pontos()

    if ponto_id not in pontos:
        return {"aceito": False, "motivo": "ponto_invalido"}

    agora = datetime.now(FUSO_LOCAL)
    _limpar_estado_se_expirado(agora)
    aguardando = aguardando_proxima_saida("principal", agora)

    # Durante uma janela de espera oficial, novas confirmações são bloqueadas
    # somente quando não existe confirmação recente que possa indicar atraso.
    if aguardando is not None and not _tem_confirmacao_recente(agora):
        return {
            "aceito": False,
            "motivo": "fora_circulacao",
            "origem": aguardando["origem"],
            "proxima": aguardando.get("proxima"),
        }

    if _estado["ponto_atual"] == ponto_id:
        return {
            "aceito": False,
            "motivo": "duplicado",
            "ponto": pontos[ponto_id]["nome"],
            "horario": _estado["horario"],
        }

    anterior = _estado["ponto_atual"]

    # Primeiro usamos o histórico inteiro, pois o último registro pode estar
    # errado. Se nada for encontrado, ainda tentamos o ponto imediatamente
    # anterior guardado no estado.
    resultado_rota = _resultado_com_historico(ponto_id)

    if resultado_rota is None and anterior is not None:
        resultado_rota = _analisar_registros_esparsos(anterior, ponto_id)

    _estado.update(
        {
            "ponto_anterior": anterior,
            "ponto_atual": ponto_id,
            "horario": agora,
            "telegram_id": telegram_id,
            "resultado_rota": resultado_rota,
        }
    )
    _registrar_no_historico(ponto_id, agora, telegram_id)

    return {
        "aceito": True,
        "primeiro_registro": anterior is None,
        "ponto": pontos[ponto_id]["nome"],
        "horario": agora,
        "resultado_rota": resultado_rota,
    }


def montar_localizacao_atual() -> str:
    """Monta a melhor resposta disponível para 'Onde está o ônibus?'.

    Prioridade quando não existe confirmação em memória:
    1. pré-saída da Garagem nos próximos 5 minutos;
    2. viagem oficial possivelmente em andamento;
    3. janela estimada posterior ao Portão 1;
    4. provável espera antes da próxima saída;
    5. saída oficial recente que ainda pode estar atrasada;
    6. ausência de informação.

    Quando existe confirmação, ela é mostrada primeiro. A rota/histórico tenta
    informar sentido e próximo ponto; se isso não for possível, o horário
    recente pode fornecer contexto apenas como estimativa.
    """
    agora = datetime.now(FUSO_LOCAL)
    _limpar_estado_se_expirado(agora)

    atual = viagem_em_andamento("principal", agora)
    retorno = viagem_em_retorno("principal", agora)
    aguardando = aguardando_proxima_saida("principal", agora)
    proxima = proximo_horario("principal", agora)

    # Sem confirmação real, a resposta é construída exclusivamente por
    # estimativas de horário. A ordem abaixo define qual hipótese tem prioridade.
    if _estado["ponto_atual"] is None:
        pre_saida_garagem = _proxima_saida_garagem_em_breve(agora)
        if pre_saida_garagem is not None:
            return _formatar_pre_saida_garagem(pre_saida_garagem)

        if atual is not None:
            return _formatar_viagem_sem_confirmacao(atual)

        if retorno is not None:
            return _formatar_retorno(retorno, proxima)

        if aguardando is not None:
            return _formatar_aguardando_saida(aguardando)

        saida_recente = _ultima_saida_oficial_recente(agora)
        if saida_recente is not None:
            return _formatar_saida_recente_sem_confirmacao(saida_recente)

        return (
            "🚌 Ainda não há confirmação de passagem nesta sessão.\n\n"
            "Use 📍 Informar passagem para registrar quando o ônibus passar por um ponto."
        )

    # A partir daqui existe ao menos uma confirmação real no estado.
    horario = _estado["horario"]
    horario_texto = horario.strftime("%H:%M:%S") if horario else "--:--"
    tempo_texto = _tempo_desde_confirmacao(horario, agora)
    ponto_id = _estado["ponto_atual"]
    ponto_nome = _nome_ponto(ponto_id)
    resultado = _estado["resultado_rota"]

    linhas = [
        f"📍 Última confirmação: {ponto_nome}",
        f"🕐 {tempo_texto} ({horario_texto})",
    ]

    # Se a confirmação aconteceu antes de uma janela de retorno calculada, a
    # situação atual pode ter avançado. Nesse caso mostramos a estimativa de
    # horário separadamente, sem apagar a confirmação registrada.
    if retorno is not None and _confirmacao_anterior_ao_retorno(horario, retorno):
        linhas.extend(["", _formatar_retorno(retorno, proxima)])
    else:
        if _possivel_atraso_portao_1(ponto_id, horario, resultado):
            linhas.extend(
                [
                    "",
                    "⚠️ Possível atraso no Portão 1",
                    "🚪 Passagem esperada por volta de 10:20.",
                    f"📍 O ônibus ainda foi confirmado em {ponto_nome}.",
                    "ℹ️ É uma estimativa, não uma confirmação de atraso.",
                ]
            )

        # Com duas evidências compatíveis, usamos a rota para informar movimento.
        if resultado is not None:
            linhas.extend(["", _formatar_movimento(resultado)])
        else:
            # Primeira confirmação: tenta usar uma saída oficial recente apenas
            # como contexto adicional para estimar sentido/próximo ponto.
            estimativa = _estimar_primeiro_registro_por_horario(ponto_id, horario)

            if estimativa is not None:
                linhas.extend(
                    [
                        "",
                        f"🕐 A confirmação é compatível com uma saída oficial recente: {estimativa['horario_saida']} — {estimativa['origem_saida']}.",
                        "➡️ Sentido provável: RUA",
                    ]
                )

                proximo = estimativa.get("proximo")
                if proximo:
                    if proximo["opcional"]:
                        linhas.extend(
                            [
                                "⏭️ Próximo esperado:",
                                f"     📍 {proximo['nome']} (se houver parada)",
                            ]
                        )
                        alternativa = proximo.get("alternativa")
                        if alternativa:
                            linhas.append(f"     ↪️ Caso não pare: {alternativa['nome']}")
                    else:
                        linhas.extend(
                            [
                                "⏭️ Próximo esperado:",
                                f"     📍 {proximo['nome']}",
                            ]
                        )

                linhas.append("ℹ️ O horário é apenas referência e pode haver atraso.")
            else:
                linhas.extend(
                    [
                        "",
                        "ℹ️ Ainda preciso de outra confirmação em um ponto diferente",
                        "para estimar o sentido e o próximo ponto.",
                    ]
                )

    return "\n".join(linhas)
