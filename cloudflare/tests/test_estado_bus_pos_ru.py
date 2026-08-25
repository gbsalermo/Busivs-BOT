import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from estado_bus import _contexto_pos_ru, _proxima_referencia_programada_mesmo_bloco

FUSO = timezone(timedelta(hours=-3))


def test_ru_fecha_1130_e_prepara_1155():
    estado = {"saida_referencia": "11:30"}

    proxima = _proxima_referencia_programada_mesmo_bloco(estado)

    assert proxima is not None
    assert proxima["hora"] == "11:55"


def test_consulta_pos_ru_nao_pula_0710_para_0725_pelo_relogio():
    estado = {
        "ponto_atual": "ru",
        "saida_referencia": "07:10",
        "resultado_rota": {
            "ponto_atual_id": "ru",
            "proximo": None,
            "fim_volta": True,
            "referencia_fechada": "06:55",
        },
    }
    agora = datetime(2026, 8, 25, 7, 10, 40, tzinfo=FUSO)

    texto = _contexto_pos_ru(estado, agora)

    assert "07:10" in texto
    assert "07:25" not in texto


def test_ultima_volta_do_bloco_nao_avanca_para_bloco_seguinte():
    estado = {"saida_referencia": "12:20"}

    assert _proxima_referencia_programada_mesmo_bloco(estado) is None
