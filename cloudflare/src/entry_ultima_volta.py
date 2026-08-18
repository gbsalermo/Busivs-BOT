from datetime import timedelta

import entry_engajamento as _entry
from entry_engajamento import *
from dados import BLOCOS_PRINCIPAL, HORARIOS
from volta_referencia import ultima_saida_oficial, viagem_por_referencia


def _minutos(hora):
    h, m = map(int, hora.split(":"))
    return h * 60 + m


def _bloco_da_viagem(hora):
    if not hora:
        return None, None
    minuto = _minutos(hora)
    for indice, bloco in enumerate(BLOCOS_PRINCIPAL):
        if _minutos(bloco["inicio"]) <= minuto <= _minutos(bloco["ultima"]):
            return indice, bloco
    return None, None


def _viagem_por_hora(hora):
    return next((v for v in HORARIOS.get("principal", []) if v.get("hora") == hora), None)


def _proxima_saida_apos_bloco(indice_bloco, agora):
    if indice_bloco is None:
        return None

    if indice_bloco + 1 < len(BLOCOS_PRINCIPAL):
        proximo_bloco = BLOCOS_PRINCIPAL[indice_bloco + 1]
        viagem = _viagem_por_hora(proximo_bloco["inicio"])
        return {
            "viagem": viagem,
            "quando": agora.replace(
                hour=int(proximo_bloco["inicio"][:2]),
                minute=int(proximo_bloco["inicio"][3:5]),
                second=0,
                microsecond=0,
            ),
            "proximo_dia_util": False,
        }

    # Último bloco do dia: a próxima saída é o primeiro bloco do próximo dia útil.
    dias = 1
    proximo_dia = agora + timedelta(days=dias)
    while proximo_dia.weekday() >= 5:
        dias += 1
        proximo_dia = agora + timedelta(days=dias)

    primeiro = BLOCOS_PRINCIPAL[0]
    viagem = _viagem_por_hora(primeiro["inicio"])
    return {
        "viagem": viagem,
        "quando": proximo_dia.replace(
            hour=int(primeiro["inicio"][:2]),
            minute=int(primeiro["inicio"][3:5]),
            second=0,
            microsecond=0,
        ),
        "proximo_dia_util": True,
    }


def _contexto_ultima_volta(estado, agora):
    viagem = viagem_por_referencia(estado) or ultima_saida_oficial(agora)
    if not viagem:
        return ""

    indice_bloco, bloco = _bloco_da_viagem(viagem.get("hora"))
    if bloco is None or viagem.get("hora") != bloco.get("ultima"):
        return ""

    proxima = _proxima_saida_apos_bloco(indice_bloco, agora)
    if not proxima or not proxima.get("viagem"):
        return ""

    viagem_proxima = proxima["viagem"]
    quando = proxima["quando"]
    origem = viagem_proxima.get("origem", "Garagem")

    if proxima.get("proximo_dia_util"):
        proxima_txt = f"{quando.strftime('%d/%m')} às {viagem_proxima['hora']} — {origem}"
    else:
        proxima_txt = f"{viagem_proxima['hora']} — {origem}"

    return (
        "🏁 Esta é a última volta deste bloco.\n"
        "🅿️ Depois desta volta, o circular segue para a Garagem.\n"
        f"⏰ Próxima saída: {proxima_txt}."
    )


class BusState(_entry.BusState):
    async def localizacao(self):
        resposta = await super().localizacao()
        status = await self.status_registro_principal()
        if not status.get("ativo"):
            return resposta

        estado = await self._carregar()
        agora = _entry.agora_local()
        contexto = _contexto_ultima_volta(estado, agora)
        if not contexto:
            return resposta

        texto = resposta.get("texto", "")
        linha_antiga = "🅿️ Sem nova saída neste bloco; o circular provavelmente segue para a Garagem."
        if linha_antiga in texto:
            texto = texto.replace(linha_antiga, contexto)
        elif contexto not in texto:
            texto += "\n\n" + contexto

        resposta["texto"] = texto
        return resposta


class Default(_entry.Default):
    pass
