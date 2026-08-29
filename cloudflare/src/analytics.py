"""Persistência mínima e isolada de analytics do BUSIVS.

Este módulo não participa das decisões de rota, referência, bloco ou
confiabilidade. Ele recebe somente eventos já produzidos pela interface e grava
agregados no Durable Object.
"""

import hashlib
import json
from datetime import timedelta

from regras import agora_local

ANALYTICS_SCHEMA_VERSION = 1
MAX_DIAS_RESUMO = 90


def _chave_usuario(telegram_id):
    """Identificador estável para deduplicação sem persistir o Telegram ID bruto."""
    bruto = str(telegram_id).encode("utf-8")
    return hashlib.sha256(bruto).hexdigest()[:24]


def _carregar_json(bruto, padrao):
    if bruto in (None, ""):
        return padrao
    if isinstance(bruto, (dict, list)):
        return bruto
    try:
        return json.loads(str(bruto))
    except Exception:
        return padrao


def _evento_normalizado(evento):
    texto = str(evento or "outro").strip().lower()
    permitido = "abcdefghijklmnopqrstuvwxyz0123456789_"
    texto = "".join(c for c in texto if c in permitido)
    return texto[:64] or "outro"


async def registrar_evento(storage, telegram_id, evento, admin=False, contar_interacao=True):
    """Registra um evento sem depender de qualquer estado operacional do ônibus."""
    if telegram_id is None:
        return {"ok": False, "motivo": "usuario_ausente"}

    agora = agora_local()
    data = agora.date().isoformat()
    evento = _evento_normalizado(evento)
    chave_dia = f"analytics:daily:{data}"

    diario = _carregar_json(await storage.get(chave_dia), {})
    diario.setdefault("schema", ANALYTICS_SCHEMA_VERSION)
    diario.setdefault("data", data)
    diario.setdefault("usuarios", [])
    diario.setdefault("interacoes", 0)
    diario.setdefault("eventos", {})
    diario.setdefault("admin_interacoes", 0)
    diario.setdefault("admin_eventos", {})
    diario.setdefault("primeiro_evento_em", agora.isoformat())
    diario["ultimo_evento_em"] = agora.isoformat()

    if admin:
        if contar_interacao:
            diario["admin_interacoes"] = int(diario.get("admin_interacoes", 0)) + 1
        admin_eventos = diario.get("admin_eventos") or {}
        admin_eventos[evento] = int(admin_eventos.get(evento, 0)) + 1
        diario["admin_eventos"] = admin_eventos
        await storage.put(chave_dia, json.dumps(diario, ensure_ascii=False))
        return {"ok": True, "admin": True}

    usuario = _chave_usuario(telegram_id)
    usuarios = diario.get("usuarios") or []
    if usuario not in usuarios:
        usuarios.append(usuario)
        diario["usuarios"] = usuarios

    if contar_interacao:
        diario["interacoes"] = int(diario.get("interacoes", 0)) + 1

    eventos = diario.get("eventos") or {}
    eventos[evento] = int(eventos.get(evento, 0)) + 1
    diario["eventos"] = eventos

    chave_usuario = f"analytics:user:{usuario}"
    perfil = _carregar_json(await storage.get(chave_usuario), {})
    novo_usuario = not bool(perfil)
    if novo_usuario:
        perfil = {
            "schema": ANALYTICS_SCHEMA_VERSION,
            "primeira_interacao_em": agora.isoformat(),
            "interacoes": 0,
        }
    perfil["ultima_interacao_em"] = agora.isoformat()
    if contar_interacao:
        perfil["interacoes"] = int(perfil.get("interacoes", 0)) + 1

    if novo_usuario:
        total = await storage.get("analytics:total_unique")
        try:
            total = int(total or 0)
        except Exception:
            total = 0
        await storage.put("analytics:total_unique", total + 1)

    await storage.put(chave_usuario, json.dumps(perfil, ensure_ascii=False))
    await storage.put(chave_dia, json.dumps(diario, ensure_ascii=False))
    await storage.put("analytics:schema_version", ANALYTICS_SCHEMA_VERSION)

    return {
        "ok": True,
        "admin": False,
        "novo_usuario": novo_usuario,
        "usuarios_unicos_dia": len(usuarios),
    }


async def resumo(storage, dias=1):
    """Agrega um período para uso futuro pelo painel administrativo."""
    try:
        dias = int(dias)
    except Exception:
        dias = 1
    dias = min(MAX_DIAS_RESUMO, max(1, dias))

    hoje = agora_local().date()
    usuarios = set()
    eventos = {}
    interacoes = 0
    admin_interacoes = 0

    for deslocamento in range(dias):
        data = (hoje - timedelta(days=deslocamento)).isoformat()
        diario = _carregar_json(await storage.get(f"analytics:daily:{data}"), {})
        usuarios.update(diario.get("usuarios") or [])
        interacoes += int(diario.get("interacoes", 0) or 0)
        admin_interacoes += int(diario.get("admin_interacoes", 0) or 0)
        for evento, quantidade in (diario.get("eventos") or {}).items():
            eventos[evento] = int(eventos.get(evento, 0)) + int(quantidade or 0)

    total = await storage.get("analytics:total_unique")
    try:
        total = int(total or 0)
    except Exception:
        total = 0

    return {
        "ok": True,
        "dias": dias,
        "usuarios_unicos": len(usuarios),
        "interacoes": interacoes,
        "eventos": eventos,
        "total_registrado": total,
        "admin_interacoes": admin_interacoes,
        "schema": ANALYTICS_SCHEMA_VERSION,
    }
