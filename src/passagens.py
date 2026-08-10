import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rota import carregar_pontos, carregar_rota, formatar_situacao_rota

FUSO_LOCAL = timezone(timedelta(hours=-3))
CAMINHO_HORARIOS = Path(__file__).resolve().parent.parent / "data" / "horarios_letivo.json"
JANELA_SAIDA_GARAGEM_MINUTOS = 35

_estado = {
    "ponto_anterior": None,
    "ponto_atual": None,
    "horario": None,
    "telegram_id": None,
    "resultado_rota": None,
}


def limpar_estado() -> None:
    _estado.update(
        {
            "ponto_anterior": None,
            "ponto_atual": None,
            "horario": None,
            "telegram_id": None,
            "resultado_rota": None,
        }
    )


def obter_estado() -> dict:
    return _estado.copy()


def _nome_ponto(ponto_id: str) -> str:
    pontos = carregar_pontos()
    ponto = pontos.get(ponto_id)
    return ponto["nome"] if ponto else ponto_id


def _ocorrencias(rota: list[dict], ponto_id: str) -> list[int]:
    return [
        indice
        for indice, item in enumerate(rota)
        if item["ponto_id"] == ponto_id
    ]


def _proximo_da_ocorrencia(rota: list[dict], indice_atual: int, pontos: dict[str, dict]) -> dict | None:
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


def _analisar_registros_esparsos(ponto_anterior: str, ponto_atual: str) -> dict | None:
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
        "sentido": item_atual["sentido_apos"],
        "proximo": _proximo_da_ocorrencia(rota, indice_atual, pontos),
    }


def _ultima_saida_recente_da_garagem(agora: datetime) -> str | None:
    with CAMINHO_HORARIOS.open("r", encoding="utf-8") as arquivo:
        horarios = json.load(arquivo)

    candidatos = []
    for viagem in horarios.get("principal", []):
        if viagem.get("origem") != "Garagem":
            continue

        hora, minuto = map(int, viagem["hora"].split(":"))
        previsto = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        diferenca = agora - previsto

        if timedelta(0) <= diferenca <= timedelta(minutes=JANELA_SAIDA_GARAGEM_MINUTOS):
            candidatos.append(previsto)

    if not candidatos:
        return None

    return max(candidatos).strftime("%H:%M")


def _estimar_primeiro_registro_por_horario(ponto_id: str, agora: datetime) -> dict | None:
    horario_garagem = _ultima_saida_recente_da_garagem(agora)
    if horario_garagem is None:
        return None

    rota = carregar_rota()
    pontos = carregar_pontos()

    ocorrencias = _ocorrencias(rota, ponto_id)
    if not ocorrencias:
        return None

    # Uma saída da Garagem inicia o percurso em direção à rua.
    # Para pontos repetidos, como Biblioteca e RU, usamos a ocorrência da ida.
    indice_atual = None
    for indice in ocorrencias:
        if rota[indice]["sentido_apos"] == "RUA":
            indice_atual = indice
            break

    if indice_atual is None:
        return None

    return {
        "horario_garagem": horario_garagem,
        "sentido": "RUA",
        "proximo": _proximo_da_ocorrencia(rota, indice_atual, pontos),
    }


def _tempo_desde_confirmacao(horario: datetime | None, agora: datetime | None = None) -> str:
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


def registrar_passagem(ponto_id: str, telegram_id: int | None = None) -> dict:
    pontos = carregar_pontos()

    if ponto_id not in pontos:
        return {"aceito": False, "motivo": "ponto_invalido"}

    if _estado["ponto_atual"] == ponto_id:
        return {
            "aceito": False,
            "motivo": "duplicado",
            "ponto": pontos[ponto_id]["nome"],
            "horario": _estado["horario"],
        }

    anterior = _estado["ponto_atual"]
    agora = datetime.now(FUSO_LOCAL)
    resultado_rota = None

    if anterior is not None:
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

    return {
        "aceito": True,
        "primeiro_registro": anterior is None,
        "ponto": pontos[ponto_id]["nome"],
        "horario": agora,
        "resultado_rota": resultado_rota,
    }


def montar_localizacao_atual() -> str:
    if _estado["ponto_atual"] is None:
        return (
            "🚌 Ainda não há confirmação de passagem nesta sessão.\n\n"
            "Use 📍 Informar passagem para registrar quando o ônibus passar por um ponto."
        )

    horario = _estado["horario"]
    horario_texto = horario.strftime("%H:%M:%S") if horario else "--:--"
    tempo_texto = _tempo_desde_confirmacao(horario)
    ponto_nome = _nome_ponto(_estado["ponto_atual"])

    linhas = [
        f"📍 Última confirmação: {ponto_nome}",
        f"🕐 {tempo_texto} ({horario_texto})",
    ]

    resultado = _estado["resultado_rota"]
    if resultado is not None:
        linhas.extend(["", formatar_situacao_rota(resultado)])
    else:
        estimativa = _estimar_primeiro_registro_por_horario(_estado["ponto_atual"], horario)

        if estimativa is not None:
            linhas.extend(
                [
                    "",
                    f"🕐 Pelo horário oficial, o ônibus deve ter saído da Garagem às {estimativa['horario_garagem']}.",
                    "➡️ Sentido provável: RUA",
                ]
            )

            proximo = estimativa.get("proximo")
            if proximo:
                if proximo["opcional"]:
                    linhas.append(f"⏭️ Próximo esperado: {proximo['nome']} (se houver parada)")
                    alternativa = proximo.get("alternativa")
                    if alternativa:
                        linhas.append(f"↪️ Caso não pare: {alternativa['nome']}")
                else:
                    linhas.append(f"⏭️ Próximo esperado: {proximo['nome']}")

            linhas.append("ℹ️ Essa indicação usa o horário previsto, não uma confirmação de saída.")
        else:
            linhas.extend(
                [
                    "",
                    "ℹ️ Ainda preciso de outra confirmação em um ponto diferente",
                    "para estimar o sentido e o próximo ponto.",
                ]
            )

    linhas.extend(
        [
            "",
            "🧪 Dados temporários desta Etapa 5. Eles são apagados ao reiniciar o bot.",
        ]
    )

    return "\n".join(linhas)
