import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from regras import estado_vazio, registrar_passagem
from transicao_bloco import confirmacao_inicia_novo_bloco
from validacao_rota import validar_deslocamento

FUSO = timezone(timedelta(hours=-3))


def _estado_anterior():
    horario = datetime(2026, 8, 17, 7, 20, tzinfo=FUSO)
    return {
        "ponto_anterior": "biblioteca",
        "ponto_atual": "ru",
        "horario": horario.isoformat(),
        "telegram_id": 1,
        "resultado_rota": {
            "ponto_atual_id": "ru",
            "indice_atual": 13,
            "sentido": "RUA",
            "proximo": None,
        },
        "historico": [
            {"ponto_id": "biblioteca", "horario": horario.isoformat(), "telegram_id": 1},
            {"ponto_id": "ru", "horario": horario.isoformat(), "telegram_id": 1},
        ],
    }


def test_ru_0730_reinicia_contexto_da_volta_0725():
    agora = datetime(2026, 8, 17, 7, 30, tzinfo=FUSO)
    estado = _estado_anterior()

    assert confirmacao_inicia_novo_bloco(estado, "ru", agora)

    estado = estado_vazio()
    estado, resultado = registrar_passagem(estado, "ru", 2, agora=agora)
    assert resultado["aceito"]

    bloqueio = validar_deslocamento(
        estado,
        "pavilhao_1",
        agora + timedelta(minutes=3),
        exigir_nova_saida_para_ciclo=True,
    )
    assert bloqueio is None


def test_ru_sem_nova_saida_nao_apaga_historico():
    agora = datetime(2026, 8, 17, 7, 22, tzinfo=FUSO)
    estado = _estado_anterior()
    assert not confirmacao_inicia_novo_bloco(estado, "ru", agora)
