import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from regras import (
    estimar_chegada_portao_1,
    listar_horarios_periodo,
    montar_resumo_horarios,
    montar_rota_atual,
    estado_vazio,
    registrar_passagem,
)

FUSO = timezone(timedelta(hours=-3))


def test_estimativa_pico_1300():
    assert estimar_chegada_portao_1("13:00")["inicio"] == "13:20"
    assert estimar_chegada_portao_1("13:00")["fim"] == "13:25"


def test_listagem_tarde_contem_1300_e_1600():
    texto = listar_horarios_periodo("tarde")
    assert "13:00" in texto
    assert "16:00" in texto


def test_resumo_noturno_aponta_2040():
    agora = datetime(2026, 8, 11, 19, 0, tzinfo=FUSO)
    texto = montar_resumo_horarios(agora)
    assert "20:40" in texto


def test_rota_contem_biblioteca_duas_vezes():
    texto = montar_rota_atual()
    assert texto.count("Biblioteca") == 2


def test_primeiro_registro_e_duplicata():
    estado = estado_vazio()
    agora = datetime(2026, 8, 11, 13, 5, tzinfo=FUSO)
    estado, resultado = registrar_passagem(estado, "fitotecnia", 1, agora)
    assert resultado["aceito"] is True
    estado, resultado = registrar_passagem(estado, "fitotecnia", 2, agora)
    assert resultado["aceito"] is False
    assert resultado["motivo"] == "duplicado"
