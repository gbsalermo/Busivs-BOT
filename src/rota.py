import json
from pathlib import Path

CAMINHO_PONTOS = Path(__file__).resolve().parent.parent / "data" / "pontos.json"
CAMINHO_ROTAS = Path(__file__).resolve().parent.parent / "data" / "rotas.json"


def carregar_pontos() -> dict[str, dict]:
    with CAMINHO_PONTOS.open("r", encoding="utf-8") as arquivo:
        pontos = json.load(arquivo)

    return {ponto["id"]: ponto for ponto in pontos}


def carregar_rota(nome_rota: str = "principal_normal") -> list[dict]:
    with CAMINHO_ROTAS.open("r", encoding="utf-8") as arquivo:
        rotas = json.load(arquivo)

    return rotas.get(nome_rota, [])


def _predecessores_validos(rota: list[dict], indice_atual: int) -> set[str]:
    """
    Retorna os pontos que podem aparecer como registro anterior ao ponto atual.

    Pontos opcionais podem ser pulados. Exemplo:
    Pavilhão II -> Portão 2 é válido caso não haja parada no
    Pavilhão de Engenharia.
    """
    predecessores = set()
    indice = indice_atual - 1

    while indice >= 0:
        item = rota[indice]
        predecessores.add(item["ponto_id"])

        if not item.get("opcional", False):
            break

        indice -= 1

    return predecessores


def _encontrar_indice_atual(
    rota: list[dict], ponto_anterior: str, ponto_atual: str
) -> int | None:
    """Localiza a ocorrência correta do ponto atual usando o ponto anterior."""
    for indice, item in enumerate(rota):
        if item["ponto_id"] != ponto_atual:
            continue

        if ponto_anterior in _predecessores_validos(rota, indice):
            return indice

    return None


def _proximo_ponto(rota: list[dict], indice_atual: int, pontos: dict[str, dict]) -> dict | None:
    indice_proximo = indice_atual + 1

    if indice_proximo >= len(rota):
        return None

    item = rota[indice_proximo]
    ponto = pontos[item["ponto_id"]]

    resultado = {
        "id": ponto["id"],
        "nome": ponto["nome"],
        "opcional": item.get("opcional", ponto.get("opcional", False)),
    }

    if resultado["opcional"]:
        indice_alternativo = indice_proximo + 1

        while indice_alternativo < len(rota):
            item_alternativo = rota[indice_alternativo]

            if not item_alternativo.get("opcional", False):
                ponto_alternativo = pontos[item_alternativo["ponto_id"]]
                resultado["alternativa"] = {
                    "id": ponto_alternativo["id"],
                    "nome": ponto_alternativo["nome"],
                }
                break

            indice_alternativo += 1

    return resultado


def analisar_trecho(
    ponto_anterior: str,
    ponto_atual: str,
    nome_rota: str = "principal_normal",
) -> dict | None:
    """
    Descobre o sentido e o próximo ponto esperado a partir das duas
    últimas confirmações de passagem.

    Retorna None quando a combinação não pertence à rota conhecida.
    """
    rota = carregar_rota(nome_rota)
    pontos = carregar_pontos()

    if ponto_anterior not in pontos or ponto_atual not in pontos:
        return None

    indice_atual = _encontrar_indice_atual(rota, ponto_anterior, ponto_atual)

    if indice_atual is None:
        return None

    item_atual = rota[indice_atual]
    ponto_atual_dados = pontos[ponto_atual]

    return {
        "ponto_anterior": pontos[ponto_anterior]["nome"],
        "ponto_atual": ponto_atual_dados["nome"],
        "sentido": item_atual["sentido_apos"],
        "proximo": _proximo_ponto(rota, indice_atual, pontos),
    }


def formatar_situacao_rota(resultado: dict | None) -> str:
    if resultado is None:
        return "Não foi possível identificar esse trecho na rota cadastrada."

    sentido = resultado["sentido"]
    seta = "➡️" if sentido == "RUA" else "⬅️"
    proximo = resultado["proximo"]

    linhas = [
        f"📍 Último ponto: {resultado['ponto_atual']}",
        f"{seta} Sentido: {sentido}",
    ]

    if proximo is None:
        linhas.append("🏁 Fim do percurso cadastrado.")
        return "\n".join(linhas)

    if proximo["opcional"]:
        linhas.append(f"⏭️ Próximo: {proximo['nome']} (se houver parada)")

        alternativa = proximo.get("alternativa")
        if alternativa:
            linhas.append(f"↪️ Caso não pare: {alternativa['nome']}")
    else:
        linhas.append(f"⏭️ Próximo: {proximo['nome']}")

    return "\n".join(linhas)
