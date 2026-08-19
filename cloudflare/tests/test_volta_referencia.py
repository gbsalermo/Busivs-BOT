import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from volta_referencia import retornar_volta_anterior, saida_ru_recente

FUSO = timezone(timedelta(hours=-3))


def test_ru_0730_fixa_referencia_0725():
    agora = datetime(2026, 8, 17, 7, 30, tzinfo=FUSO)
    viagem = saida_ru_recente(agora)
    assert viagem is not None
    assert viagem["hora"] == "07:25"


def test_ru_1254_mantem_referencia_1220_em_pico():
    agora = datetime(2026, 8, 19, 12, 54, tzinfo=FUSO)
    viagem = saida_ru_recente(agora)

    assert viagem is not None
    assert viagem["hora"] == "12:20"


def test_ru_1330_prefere_nova_saida_1325():
    agora = datetime(2026, 8, 19, 13, 30, tzinfo=FUSO)
    viagem = saida_ru_recente(agora)

    assert viagem is not None
    assert viagem["hora"] == "13:25"


def test_admin_retorna_de_0740_para_0725_sem_apagar_estado():
    agora = datetime(2026, 8, 17, 7, 47, tzinfo=FUSO)
    estado = {
        "ponto_anterior": "solos_neas_florestal",
        "ponto_atual": "pavilhao_1",
        "horario": agora.isoformat(),
        "telegram_id": 1,
        "resultado_rota": {"sentido": "RUA"},
        "historico": [{"ponto_id": "pavilhao_1", "horario": agora.isoformat()}],
    }

    ajustado, viagem = retornar_volta_anterior(estado, agora)

    assert viagem is not None
    assert viagem["hora"] == "07:25"
    assert ajustado["saida_referencia"] == "07:25"
    assert ajustado["saida_referencia_manual"] is True
    assert ajustado["ponto_atual"] == "pavilhao_1"
    assert ajustado["historico"]
