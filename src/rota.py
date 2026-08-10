"""Leitura e interpretação da rota física do Circular UFRB.

Este módulo trabalha somente com a estrutura da rota: pontos, ordem de
passagem, pontos opcionais, sentido e próximo ponto esperado. Ele não guarda
estado do ônibus e não usa horário oficial; essas responsabilidades ficam em
``passagens.py`` e ``horarios.py``.

A principal dificuldade da rota é que alguns pontos aparecem mais de uma vez
(ex.: Biblioteca e RU) e alguns podem ser pulados. Por isso o sentido nunca é
inferido apenas pelo nome do ponto atual: o ponto anterior também é usado.
"""

import json
from pathlib import Path

# Arquivos de dados permanentes. Alterações de pontos ou sequência devem ser
# feitas nos JSONs, sem espalhar a rota diretamente pelo código.
CAMINHO_PONTOS = Path(__file__).resolve().parent.parent / "data" / "pontos.json"
CAMINHO_ROTAS = Path(__file__).resolve().parent.parent / "data" / "rotas.json"


def carregar_pontos() -> dict[str, dict]:
    """Carrega os pontos cadastrados e indexa cada um pelo seu ``id``.

    O JSON armazena uma lista. O dicionário retornado facilita buscas como
    ``pontos['biblioteca']`` sem percorrer a lista inteira a cada consulta.
    """
    with CAMINHO_PONTOS.open("r", encoding="utf-8") as arquivo:
        pontos = json.load(arquivo)

    return {ponto["id"]: ponto for ponto in pontos}


def carregar_rota(nome_rota: str = "principal_normal") -> list[dict]:
    """Carrega a sequência de uma rota pelo nome.

    Args:
        nome_rota: chave existente em ``data/rotas.json``.

    Returns:
        Lista ordenada dos pontos da rota ou lista vazia quando ela não existe.
    """
    with CAMINHO_ROTAS.open("r", encoding="utf-8") as arquivo:
        rotas = json.load(arquivo)

    return rotas.get(nome_rota, [])


def _predecessores_validos(rota: list[dict], indice_atual: int) -> set[str]:
    """Descobre quais pontos podem preceder a ocorrência atual da rota.

    O ponto imediatamente anterior é sempre aceito. Se houver pontos opcionais
    antes da posição atual, eles podem ter sido pulados; por isso a busca volta
    até encontrar o primeiro ponto obrigatório.

    Exemplo: ``Pavilhão II -> Portão 2`` continua válido quando o Pavilhão de
    Engenharia, que é opcional, não foi atendido.
    """
    predecessores = set()
    indice = indice_atual - 1

    while indice >= 0:
        item = rota[indice]
        predecessores.add(item["ponto_id"])

        # Ao chegar a um ponto obrigatório, não faz sentido continuar voltando:
        # ele delimita o trecho válido anterior à ocorrência atual.
        if not item.get("opcional", False):
            break

        indice -= 1

    return predecessores


def _encontrar_indice_atual(
    rota: list[dict], ponto_anterior: str, ponto_atual: str
) -> int | None:
    """Localiza qual ocorrência do ponto atual combina com o ponto anterior.

    Isso resolve pontos repetidos na rota. A Biblioteca, por exemplo, pode ser
    a da ida ou a da volta; o predecessor indica qual ocorrência é a correta.
    """
    for indice, item in enumerate(rota):
        if item["ponto_id"] != ponto_atual:
            continue

        if ponto_anterior in _predecessores_validos(rota, indice):
            return indice

    return None


def _proximo_ponto(
    rota: list[dict], indice_atual: int, pontos: dict[str, dict]
) -> dict | None:
    """Monta os dados do próximo ponto depois da ocorrência atual.

    Quando o próximo ponto é opcional, também informa a primeira alternativa
    obrigatória seguinte. Assim a interface pode exibir tanto "se houver
    parada" quanto "caso não pare".
    """
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

        # Pode haver mais de um opcional em sequência; procura o próximo ponto
        # obrigatório para oferecer uma referência segura ao usuário.
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
    """Infere sentido e próximo ponto usando duas confirmações consecutivas.

    Args:
        ponto_anterior: ID da confirmação anterior.
        ponto_atual: ID da confirmação mais recente.
        nome_rota: rota usada como referência.

    Returns:
        Dicionário com trecho, sentido e próximo ponto, ou ``None`` quando a
        combinação não pertence à rota conhecida.

    Importante: esta função interpreta somente a geometria da rota. Ela não
    decide se a confirmação é recente, se o ônibus está em circulação ou se
    existe atraso.
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
        "ponto_atual_id": ponto_atual,
        "ponto_atual_opcional": item_atual.get(
            "opcional", ponto_atual_dados.get("opcional", False)
        ),
        "sentido": item_atual["sentido_apos"],
        "proximo": _proximo_ponto(rota, indice_atual, pontos),
    }


def formatar_situacao_rota(resultado: dict | None) -> str:
    """Transforma o resultado técnico de ``analisar_trecho`` em texto legível.

    Esta função é usada principalmente pelo simulador/testes manuais. Ela trata
    o encerramento no RU e a apresentação diferenciada dos pontos opcionais.
    """
    if resultado is None:
        return "Não foi possível identificar esse trecho na rota cadastrada."

    proximo = resultado["proximo"]

    # O RU aparece também como término da volta. Nessa ocorrência, não existe
    # próximo ponto dentro da mesma sequência cadastrada.
    if proximo is None and resultado.get("ponto_atual_id") == "ru":
        return (
            f"📍 Último ponto: {resultado['ponto_atual']}\n"
            "🏁 Percurso encerrado no RU."
        )

    sentido = resultado["sentido"]
    seta = "➡️" if sentido == "RUA" else "⬅️"

    ponto_referencia = resultado["ponto_atual"]
    rotulo_ponto = "📍 Último ponto"

    # Pontos opcionais não são uma referência tão forte, pois o ônibus pode
    # passar sem efetivamente parar. Nesses casos mostramos o ponto obrigatório
    # anterior como referência visual.
    ponto_opcional = resultado.get("ponto_atual_opcional", False)
    if not ponto_opcional:
        ponto_opcional = resultado.get("ponto_atual") in {
            "Pavilhão de Engenharia",
            "Torre / COTEC",
        }

    if ponto_opcional and resultado.get("ponto_anterior"):
        ponto_referencia = resultado["ponto_anterior"]
        rotulo_ponto = "📍 Último ponto de referência"

    linhas = [
        f"{rotulo_ponto}: {ponto_referencia}",
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
