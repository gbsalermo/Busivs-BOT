from datetime import datetime

from dados import PONTOS, ROTA

MAX_HISTORICO = 40


def _iso(agora):
    return agora.isoformat()


def _dt(valor):
    try:
        return datetime.fromisoformat(str(valor)) if valor else None
    except Exception:
        return None


def _ocorrencias(ponto_id):
    return [i for i, item in enumerate(ROTA) if item["ponto_id"] == ponto_id]


def _proximo(indice):
    if indice + 1 >= len(ROTA):
        return None
    item = ROTA[indice + 1]
    ponto = PONTOS[item["ponto_id"]]
    proximo = {
        "id": ponto["id"],
        "nome": ponto["nome"],
        "opcional": item.get("opcional", ponto.get("opcional", False)),
    }
    if proximo["opcional"]:
        for j in range(indice + 2, len(ROTA)):
            seguinte = ROTA[j]
            if seguinte.get("opcional", False):
                continue
            p = PONTOS[seguinte["ponto_id"]]
            proximo["alternativa"] = {"id": p["id"], "nome": p["nome"]}
            break
    return proximo


def _analisar(anterior, atual):
    if anterior not in PONTOS or atual not in PONTOS:
        return None
    candidatos = []
    for ia in _ocorrencias(anterior):
        for ib in _ocorrencias(atual):
            if ib > ia:
                candidatos.append((ib - ia, ib))
    if not candidatos:
        return None
    _, indice = min(candidatos, key=lambda x: x[0])
    item = ROTA[indice]
    return {
        "ponto_anterior": PONTOS[anterior]["nome"],
        "ponto_atual": PONTOS[atual]["nome"],
        "ponto_atual_id": atual,
        "indice_atual": indice,
        "sentido": item["sentido_apos"],
        "proximo": _proximo(indice),
    }


def _resultado_historico(historico, ponto_id):
    total = len(historico)
    for i in range(total - 1, -1, -1):
        registro = historico[i]
        anterior = registro.get("ponto_id")
        if anterior == ponto_id:
            continue
        resultado = _analisar(anterior, ponto_id)
        if resultado:
            resultado["base_historico"] = {
                "ponto_id": anterior,
                "horario": registro.get("horario"),
                "telegram_id": registro.get("telegram_id"),
            }
            resultado["ignorou_registro_incompativel"] = i != total - 1
            return resultado
    return None


def _resultado_primeiro_ponto(ponto_id):
    if ponto_id == "biblioteca":
        return {
            "ponto_atual_id": "biblioteca",
            "biblioteca_ambigua": True,
            "motivo": "primeira_confirmacao_sem_contexto",
        }
    if ponto_id == "ru":
        indice = next((i for i, item in enumerate(ROTA) if item["ponto_id"] == "ru"), None)
        if indice is None:
            return {
                "ponto_atual_id": "ru",
                "sentido": None,
                "proximo": None,
                "ru_primeiro_ponto": True,
            }
        return {
            "ponto_anterior": None,
            "ponto_atual": PONTOS["ru"]["nome"],
            "ponto_atual_id": "ru",
            "indice_atual": indice,
            "sentido": ROTA[indice]["sentido_apos"],
            "proximo": _proximo(indice),
            "ru_primeiro_ponto": True,
        }
    ocorrencias = _ocorrencias(ponto_id)
    if len(ocorrencias) != 1:
        return None
    indice = ocorrencias[0]
    item = ROTA[indice]
    return {
        "ponto_anterior": None,
        "ponto_atual": PONTOS[ponto_id]["nome"],
        "ponto_atual_id": ponto_id,
        "indice_atual": indice,
        "sentido": item["sentido_apos"],
        "proximo": _proximo(indice),
    }


def registrar_sem_relogio(estado, ponto_id, telegram_id, agora):
    """Registra uma confirmação usando somente a rota e evidências anteriores.

    Não consulta horários do Principal, não bloqueia por janela e não usa o
    relógio para trocar de volta. A validade operacional do veículo deve ser
    verificada pela camada chamadora.
    """
    estado = dict(estado or {})
    if ponto_id not in PONTOS:
        return estado, {"aceito": False, "motivo": "ponto_invalido"}

    horario_anterior = _dt(estado.get("horario"))
    if horario_anterior and horario_anterior.date() != agora.date():
        estado = {
            "ponto_anterior": None,
            "ponto_atual": None,
            "horario": None,
            "telegram_id": None,
            "resultado_rota": None,
            "historico": [],
        }

    if estado.get("ponto_atual") == ponto_id:
        return estado, {
            "aceito": False,
            "motivo": "duplicado",
            "ponto": PONTOS[ponto_id]["nome"],
        }

    anterior = estado.get("ponto_atual")
    historico = list(estado.get("historico", []))
    resultado = _resultado_historico(historico, ponto_id)
    if resultado is None and anterior:
        resultado = _analisar(anterior, ponto_id)
    if anterior is None:
        resultado = _resultado_primeiro_ponto(ponto_id)

    if ponto_id == "ru" and anterior is not None:
        if resultado is None:
            resultado = {"ponto_atual_id": "ru", "sentido": None, "proximo": None}
        resultado["fim_volta"] = True
        resultado["proximo"] = None

    registro = {
        "ponto_id": ponto_id,
        "horario": _iso(agora),
        "telegram_id": telegram_id,
    }
    novo = {
        "ponto_anterior": anterior,
        "ponto_atual": ponto_id,
        "horario": _iso(agora),
        "telegram_id": telegram_id,
        "resultado_rota": resultado,
        "historico": (historico + [registro])[-MAX_HISTORICO:],
    }

    for chave, valor in estado.items():
        if chave not in novo and chave not in {"confirmacao_nao_confiavel"}:
            novo[chave] = valor

    return novo, {
        "aceito": True,
        "primeiro_registro": anterior is None,
        "ponto": PONTOS[ponto_id]["nome"],
        "resultado_rota": resultado,
        "fim_volta": ponto_id == "ru" and anterior is not None,
    }


def reiniciar_posicao_para_nova_volta(estado):
    """Zera somente a inferência posicional; a referência pode ser preservada."""
    estado = dict(estado or {})
    novo = {
        "ponto_anterior": None,
        "ponto_atual": None,
        "horario": None,
        "telegram_id": None,
        "resultado_rota": None,
        "historico": [],
    }
    for chave, valor in estado.items():
        if chave not in novo and chave not in {"confirmacao_nao_confiavel"}:
            novo[chave] = valor
    return novo


def evidencia_nova_volta(estado, ponto_novo):
    """Detecta reinício pela rota, nunca apenas pelo horário."""
    if not estado or not estado.get("ponto_atual"):
        return False

    ponto_atual = estado.get("ponto_atual")
    resultado = estado.get("resultado_rota") or {}

    pontos_ida = {
        "fitotecnia",
        "solos_neas_florestal",
        "pavilhao_1",
        "biblioteca",
        "pavilhao_2",
        "pavilhao_engenharia",
        "portao_2",
        "ponto_externo_1",
        "ponto_externo_2",
        "portao_1",
    }
    pontos_ida_iniciais = {
        "fitotecnia",
        "solos_neas_florestal",
        "pavilhao_1",
    }

    if ponto_atual == "ru" and ponto_novo in pontos_ida:
        return True

    if resultado.get("sentido") == "RU" and ponto_novo in pontos_ida_iniciais:
        return True

    return False


def texto_localizacao_colaborativa(estado, agora, titulo="🚐 Micro"):
    """Localização sem inferências de horário do Circular Principal."""
    if not estado or not estado.get("ponto_atual"):
        return f"{titulo}\n\nAinda não há confirmação de passagem nesta sessão."

    ponto_id = estado.get("ponto_atual")
    nome = PONTOS.get(ponto_id, {}).get("nome", ponto_id)
    horario = _dt(estado.get("horario"))
    if horario:
        segundos = max(0, int((agora - horario).total_seconds()))
        if segundos < 60:
            tempo = "agora mesmo"
        elif segundos < 3600:
            tempo = f"há {segundos // 60} min"
        else:
            horas = segundos // 3600
            minutos = (segundos % 3600) // 60
            tempo = f"há {horas}h" if minutos == 0 else f"há {horas}h {minutos}min"
        hora_txt = horario.strftime("%H:%M:%S")
    else:
        tempo = "horário desconhecido"
        hora_txt = "--:--"

    linhas = [titulo, "", f"📍 Última confirmação: {nome}", f"🕐 {tempo} ({hora_txt})"]
    resultado = estado.get("resultado_rota") or {}

    if resultado.get("ru_primeiro_ponto"):
        proximo = resultado.get("proximo")
        linhas += ["", "🚌 Passagem pelo RU confirmada no início do percurso."]
        if proximo:
            linhas += ["⏭️ Próximo esperado:", f"     📍 {proximo['nome']}"]
        linhas.append("➡️ Sentido: RUA")
        return "\n".join(linhas)

    if ponto_id == "ru" or resultado.get("fim_volta"):
        linhas += ["", "🏁 Chegada ao RU — fim da volta.", "🔄 Uma nova volta só será assumida quando outro ponto indicar o reinício."]
        return "\n".join(linhas)

    if resultado.get("biblioteca_ambigua"):
        linhas += ["", "↔️ Sentido ainda indeterminado.", "ℹ️ A Biblioteca aparece na ida e no retorno da rota.", "📍 Outra confirmação definirá o sentido."]
        return "\n".join(linhas)

    sentido = resultado.get("sentido")
    proximo = resultado.get("proximo")
    if sentido:
        seta = "➡️" if sentido == "RUA" else "⬅️"
        if proximo:
            linhas += ["", "⏭️ Próximo:", f"     📍 {proximo['nome']}" + (" (se houver parada)" if proximo.get("opcional") else "")]
            if proximo.get("alternativa"):
                linhas.append(f"     ↪️ Caso não pare: {proximo['alternativa']['nome']}")
        linhas.append(f"{seta} Sentido: {sentido}")
    else:
        linhas += ["", "ℹ️ Ainda preciso de outra confirmação para definir o sentido."]

    return "\n".join(linhas)
