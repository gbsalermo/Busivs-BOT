import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from regras import estado_vazio, registrar_passagem
from transicao_bloco import confirmacao_inicia_novo_bloco
from validacao_rota import validar_deslocamento

FUSO = timezone(timedelta(hours=-3))


def _estado_anterior(horario=None, referencia=None, manual=False):
    horario = horario or datetime(2026, 8, 17, 7, 20, tzinfo=FUSO)
    estado = {
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
    if referencia:
        estado["saida_referencia"] = referencia
        estado["saida_referencia_manual"] = bool(manual)
    return estado


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


def test_ru_atrasado_da_volta_anterior_pode_abrir_0725_por_referencia():
    estado = _estado_anterior(
        horario=datetime(2026, 8, 18, 7, 29, tzinfo=FUSO),
        referencia="07:10",
    )
    agora = datetime(2026, 8, 18, 7, 32, tzinfo=FUSO)

    assert confirmacao_inicia_novo_bloco(estado, "ru", agora)

    novo = estado_vazio()
    novo, resultado = registrar_passagem(novo, "ru", 2, agora=agora)
    assert resultado["aceito"]

    bloqueio_fitotecnia = validar_deslocamento(
        novo,
        "fitotecnia",
        agora + timedelta(minutes=1),
        exigir_nova_saida_para_ciclo=True,
    )
    assert bloqueio_fitotecnia is None

    novo, resultado_fitotecnia = registrar_passagem(
        novo,
        "fitotecnia",
        2,
        agora=agora + timedelta(minutes=1),
    )
    assert resultado_fitotecnia["aceito"]

    bloqueio_solos = validar_deslocamento(
        novo,
        "solos_neas_florestal",
        agora + timedelta(minutes=2),
        exigir_nova_saida_para_ciclo=True,
    )
    assert bloqueio_solos is None


def test_ru_nao_reabre_quando_estado_ja_e_da_volta_0725():
    estado = _estado_anterior(
        horario=datetime(2026, 8, 18, 7, 30, tzinfo=FUSO),
        referencia="07:25",
    )
    agora = datetime(2026, 8, 18, 7, 32, tzinfo=FUSO)

    assert not confirmacao_inicia_novo_bloco(estado, "ru", agora)


def test_ru_respeita_referencia_manual_1300_mesmo_apos_1325():
    estado = _estado_anterior(
        horario=datetime(2026, 8, 19, 13, 20, tzinfo=FUSO),
        referencia="13:00",
        manual=True,
    )
    agora = datetime(2026, 8, 19, 13, 27, tzinfo=FUSO)

    assert not confirmacao_inicia_novo_bloco(estado, "ru", agora)
    assert estado["saida_referencia"] == "13:00"
    assert estado["saida_referencia_manual"] is True
