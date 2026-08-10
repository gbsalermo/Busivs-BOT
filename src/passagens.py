from datetime import datetime, timedelta, timezone

from rota import carregar_pontos, carregar_rota, formatar_situacao_rota

FUSO_LOCAL = timezone(timedelta(hours=-3))

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

    proximo = None
    if indice_atual + 1 < len(rota):
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

    return {
        "ponto_anterior": pontos[ponto_anterior]["nome"],
        "ponto_atual": pontos[ponto_atual]["nome"],
        "sentido": item_atual["sentido_apos"],
        "proximo": proximo,
    }


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
    ponto_nome = _nome_ponto(_estado["ponto_atual"])

    linhas = [
        f"📍 Última confirmação: {ponto_nome}",
        f"🕐 Horário: {horario_texto}",
    ]

    resultado = _estado["resultado_rota"]
    if resultado is None:
        linhas.extend(
            [
                "",
                "ℹ️ Ainda preciso de outra confirmação em um ponto diferente",
                "para estimar o sentido e o próximo ponto.",
            ]
        )
    else:
        linhas.extend(["", formatar_situacao_rota(resultado)])

    linhas.extend(
        [
            "",
            "🧪 Dados temporários desta Etapa 3. Eles são apagados ao reiniciar o bot.",
        ]
    )

    return "\n".join(linhas)
