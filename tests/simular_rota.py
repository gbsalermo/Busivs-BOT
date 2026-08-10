from pathlib import Path
import sys

PASTA_RAIZ = Path(__file__).resolve().parent.parent
PASTA_SRC = PASTA_RAIZ / "src"

if str(PASTA_SRC) not in sys.path:
    sys.path.insert(0, str(PASTA_SRC))

from rota import analisar_trecho, formatar_situacao_rota


CENARIOS = [
    ("ru", "fitotecnia"),
    ("fitotecnia", "solos_neas_florestal"),
    ("solos_neas_florestal", "pavilhao_1"),
    ("pavilhao_1", "biblioteca"),
    ("biblioteca", "pavilhao_2"),
    ("pavilhao_2", "pavilhao_engenharia"),
    ("pavilhao_engenharia", "portao_2"),
    ("portao_2", "ponto_externo_1"),
    ("ponto_externo_1", "ponto_externo_2"),
    ("ponto_externo_2", "portao_1"),
    ("portao_1", "biblioteca"),
    ("biblioteca", "torre_cotec"),
    ("torre_cotec", "ru"),
]


CENARIOS_COM_PULO_OPCIONAL = [
    ("pavilhao_2", "portao_2"),
    ("biblioteca", "ru"),
]


def _mostrar_cenario(numero: int, ponto_anterior: str, ponto_atual: str) -> None:
    resultado = analisar_trecho(ponto_anterior, ponto_atual)

    print(f"\n--- Cenário {numero} ---")
    print(f"Registro anterior: {ponto_anterior}")
    print(f"Registro atual:    {ponto_atual}")
    print()
    print(formatar_situacao_rota(resultado))


def simular_rota_completa() -> None:
    print("\n========================================")
    print("SIMULAÇÃO MANUAL - ROTA COMPLETA")
    print("========================================")

    for numero, (anterior, atual) in enumerate(CENARIOS, start=1):
        _mostrar_cenario(numero, anterior, atual)


def simular_pulos_opcionais() -> None:
    print("\n========================================")
    print("SIMULAÇÃO - PONTOS OPCIONAIS PULADOS")
    print("========================================")

    for numero, (anterior, atual) in enumerate(CENARIOS_COM_PULO_OPCIONAL, start=1):
        _mostrar_cenario(numero, anterior, atual)


def simular_interativo() -> None:
    print("\n========================================")
    print("SIMULAÇÃO INTERATIVA")
    print("========================================")
    print("Digite os IDs dos dois últimos pontos.")
    print("Exemplo: ponto_externo_2 e portao_1")
    print("Digite 'sair' a qualquer momento para encerrar.\n")

    while True:
        anterior = input("Ponto anterior: ").strip()
        if anterior.lower() == "sair":
            break

        atual = input("Ponto atual:    ").strip()
        if atual.lower() == "sair":
            break

        resultado = analisar_trecho(anterior, atual)
        print()
        print(formatar_situacao_rota(resultado))
        print()


def main() -> None:
    while True:
        print("\n========================================")
        print("BUSIVS BOT - SIMULADOR DE ROTA")
        print("========================================")
        print("1 - Simular rota completa")
        print("2 - Simular pulos dos pontos opcionais")
        print("3 - Testar um trecho manualmente")
        print("0 - Sair")

        opcao = input("\nEscolha: ").strip()

        if opcao == "1":
            simular_rota_completa()
        elif opcao == "2":
            simular_pulos_opcionais()
        elif opcao == "3":
            simular_interativo()
        elif opcao == "0":
            print("Simulação encerrada.")
            break
        else:
            print("Opção inválida.")


if __name__ == "__main__":
    main()
