import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from validacao_rota import validar_deslocamento

FUSO = timezone(timedelta(hours=-3))


def _estado(ponto, horario):
    return {
        "ponto_anterior": None,
        "ponto_atual": ponto,
        "horario": horario.isoformat(),
        "telegram_id": 1,
        "resultado_rota": None,
        "historico": [],
    }


def test_biblioteca_para_pavilhao_1_em_segundos_e_bloqueado():
    inicio = datetime(2026, 8, 11, 10, 0, tzinfo=FUSO)
    bloqueio = validar_deslocamento(_estado("biblioteca", inicio), "pavilhao_1", inicio + timedelta(seconds=10))
    assert bloqueio is not None
    assert bloqueio["motivo"] == "deslocamento_improvavel"


def test_pavilhao_1_para_ru_em_segundos_e_bloqueado():
    inicio = datetime(2026, 8, 11, 10, 0, tzinfo=FUSO)
    bloqueio = validar_deslocamento(_estado("pavilhao_1", inicio), "ru", inicio + timedelta(seconds=20))
    assert bloqueio is not None
    assert bloqueio["motivo"] == "deslocamento_improvavel"


def test_pontos_proximos_nao_sao_bloqueados_por_tempo():
    inicio = datetime(2026, 8, 11, 10, 0, tzinfo=FUSO)
    bloqueio = validar_deslocamento(_estado("ponto_externo_1", inicio), "ponto_externo_2", inicio + timedelta(seconds=2))
    assert bloqueio is None


def test_salto_longo_e_aceito_depois_de_tempo_plausivel():
    inicio = datetime(2026, 8, 11, 10, 0, tzinfo=FUSO)
    bloqueio = validar_deslocamento(_estado("pavilhao_1", inicio), "ru", inicio + timedelta(minutes=5))
    assert bloqueio is None
