import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from registro_colaborativo import evidencia_nova_volta, registrar_sem_relogio

FUSO = timezone(timedelta(hours=-3))


def _vazio():
    return {
        "ponto_anterior": None,
        "ponto_atual": None,
        "horario": None,
        "telegram_id": None,
        "resultado_rota": None,
        "historico": [],
    }


def test_primeira_biblioteca_fica_ambigua_sem_usar_horario():
    agora = datetime(2026, 8, 19, 12, 37, tzinfo=FUSO)
    estado, resultado = registrar_sem_relogio(_vazio(), "biblioteca", 1, agora)

    assert resultado["aceito"]
    assert estado["resultado_rota"]["biblioteca_ambigua"] is True
    assert estado["resultado_rota"].get("sentido") is None


def test_biblioteca_repetida_antes_de_15_min_continua_duplicada():
    agora = datetime(2026, 8, 24, 11, 30, tzinfo=FUSO)
    estado, primeiro = registrar_sem_relogio(_vazio(), "biblioteca", 1, agora)
    assert primeiro["aceito"]

    estado2, repetido = registrar_sem_relogio(
        estado,
        "biblioteca",
        2,
        agora + timedelta(minutes=14, seconds=59),
    )

    assert repetido["aceito"] is False
    assert repetido["motivo"] == "duplicado"
    assert estado2["horario"] == estado["horario"]


def test_biblioteca_repetida_apos_15_min_vira_passagem_de_retorno():
    agora = datetime(2026, 8, 24, 11, 30, tzinfo=FUSO)
    estado, primeiro = registrar_sem_relogio(_vazio(), "biblioteca", 1, agora)
    assert primeiro["aceito"]

    estado, retorno = registrar_sem_relogio(
        estado,
        "biblioteca",
        2,
        agora + timedelta(minutes=16),
    )

    assert retorno["aceito"] is True
    assert retorno["reconfirmacao_biblioteca"] is True
    assert estado["resultado_rota"]["sentido"] == "RU"
    assert estado["resultado_rota"]["reconfirmacao_biblioteca"] is True
    assert estado["resultado_rota"]["proximo"]["id"] == "torre_cotec"


def test_ru_confiavel_significa_fim_da_volta():
    agora = datetime(2026, 8, 19, 7, 50, tzinfo=FUSO)
    estado, _ = registrar_sem_relogio(_vazio(), "portao_1", 1, agora)
    estado, resultado = registrar_sem_relogio(estado, "ru", 2, agora + timedelta(minutes=5))

    assert resultado["aceito"]
    assert resultado["fim_volta"] is True
    assert estado["resultado_rota"]["fim_volta"] is True
    assert estado["resultado_rota"]["proximo"] is None


def test_ru_seguido_de_fitotecnia_e_evidencia_de_nova_volta():
    agora = datetime(2026, 8, 19, 7, 50, tzinfo=FUSO)
    estado, _ = registrar_sem_relogio(_vazio(), "ru", 1, agora)

    assert evidencia_nova_volta(estado, "fitotecnia") is True
    assert evidencia_nova_volta(estado, "solos_neas_florestal") is True
    assert evidencia_nova_volta(estado, "pavilhao_1") is True


def test_retorno_p1_para_biblioteca_nao_abre_nova_volta():
    agora = datetime(2026, 8, 19, 7, 50, tzinfo=FUSO)
    estado, _ = registrar_sem_relogio(_vazio(), "portao_1", 1, agora)

    assert estado["resultado_rota"]["sentido"] == "RU"
    assert evidencia_nova_volta(estado, "biblioteca") is False
    assert evidencia_nova_volta(estado, "fitotecnia") is True


def test_registro_colaborativo_nao_depende_da_grade_do_principal():
    agora = datetime(2026, 8, 19, 19, 17, tzinfo=FUSO)
    estado, resultado = registrar_sem_relogio(_vazio(), "solos_neas_florestal", 1, agora)

    assert resultado["aceito"] is True
    assert estado["ponto_atual"] == "solos_neas_florestal"
