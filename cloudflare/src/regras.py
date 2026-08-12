from datetime import datetime, timedelta, timezone
from dados import HORARIOS, PONTOS, ROTA

FUSO_LOCAL = timezone(timedelta(hours=-3))
MARGEM_RETORNO_MINUTOS = 5
DURACAO_RETORNO_MINUTOS = 15
JANELA_SAIDA_RECENTE_MINUTOS = 45
JANELA_PRE_SAIDA_GARAGEM_MINUTOS = 5
JANELA_CONFIRMACAO_RECENTE_MINUTOS = 30
LIMITE_INTERVALO_BLOCO_MINUTOS = 60
MAX_HISTORICO_REGISTROS = 20

TITULOS_PERIODOS = {
    "manha":"🌅 <b>Horários da manhã</b>",
    "meio_dia":"🍽️ <b>Horários do almoço</b>",
    "tarde":"🌤️ <b>Horários da tarde</b>",
    "noite":"🌙 <b>Horários da noite</b>",
}

def agora_local():
    return datetime.now(FUSO_LOCAL)

def _minutos(h):
    hh, mm = map(int, h.split(":")); return hh*60+mm

def _fmt_min(total):
    total %= 1440; return f"{total//60:02d}:{total%60:02d}"

def _nome_origem(origem):
    s=origem.strip().lower()
    if "ru" in s: return "RU"
    if "garagem" in s: return "Garagem"
    return origem

def estimar_chegada_portao_1(hora_saida):
    m=_minutos(hora_saida)
    pico=(_minutos("07:30")<=m<=_minutos("08:00") or _minutos("11:30")<=m<=_minutos("14:00") or _minutos("17:30")<=m<=_minutos("18:15"))
    minimo,maximo=(20,25) if pico else (15,20)
    return {"inicio":_fmt_min(m+minimo),"fim":_fmt_min(m+maximo),"pico":pico,"noturno":m>=_minutos("20:00")}

def proximo_horario(agora=None):
    agora=agora or agora_local(); ma=agora.hour*60+agora.minute
    for h in HORARIOS["principal"]:
        if _minutos(h["hora"])>ma: return h
    return None

def viagem_em_andamento(agora=None):
    agora=agora or agora_local(); ma=agora.hour*60+agora.minute; cand=[]
    for h in HORARIOS["principal"]:
        p=estimar_chegada_portao_1(h["hora"])
        if _minutos(h["hora"])<=ma<=_minutos(p["fim"]): cand.append(h)
    return max(cand,key=lambda x:_minutos(x["hora"])) if cand else None

def viagem_em_retorno(agora=None):
    agora=agora or agora_local(); ma=agora.hour*60+agora.minute; hs=HORARIOS["principal"]
    for i,h in enumerate(hs):
        p=estimar_chegada_portao_1(h["hora"]); ini=_minutos(p["fim"])+MARGEM_RETORNO_MINUTOS
        prox=_minutos(hs[i+1]["hora"]) if i+1<len(hs) else 1440; fim=min(ini+DURACAO_RETORNO_MINUTOS,prox)
        if ini<=ma<fim:
            return {"viagem":h,"origem":_nome_origem(h["origem"]),"inicio_retorno":_fmt_min(ini),"fim_retorno":_fmt_min(fim),"proxima":hs[i+1] if i+1<len(hs) else None}
    return None

def aguardando_proxima_saida(agora=None):
    agora=agora or agora_local(); ma=agora.hour*60+agora.minute; hs=HORARIOS["principal"]
    for i,h in enumerate(hs[:-1]):
        p=estimar_chegada_portao_1(h["hora"]); ini=_minutos(p["fim"])+MARGEM_RETORNO_MINUTOS; fim=ini+DURACAO_RETORNO_MINUTOS
        prox=hs[i+1]; ps=_minutos(prox["hora"])
        if fim<=ma<ps: return {"origem":_nome_origem(prox["origem"]),"proxima":prox}
    return None

def _pertence(h, periodo):
    m=_minutos(h)
    if periodo=="manha": return m<=_minutos("12:20")
    if periodo=="meio_dia": return _minutos("11:30")<=m<=_minutos("13:25")
    if periodo=="tarde": return _minutos("13:00")<=m<_minutos("17:30")
    if periodo=="noite": return m>=_minutos("17:30")
    return False

def _periodo(agora):
    m=agora.hour*60+agora.minute
    if m<_minutos("11:30"): return "🌅","Manhã"
    if m<_minutos("13:00"): return "🍽️","Almoço"
    if m<_minutos("17:30"): return "🌤️","Tarde"
    return "🌙","Noite"

def _frase_saida(origem):
    n=_nome_origem(origem)
    return "Sai da Garagem" if n=="Garagem" else "Sai do RU" if n=="RU" else f"Sai de {n}"

def _volta(h,n):
    p=estimar_chegada_portao_1(h["hora"]); pico=" ⚠️ pico" if p["pico"] else ""
    return [f"<b>{n}ª volta</b>",f"  {_frase_saida(h['origem'])}: <b>{h['hora']}</b>{pico}",f"  🚪 Chega no Portão 1: <b>{p['inicio']}–{p['fim']}</b>"]

def montar_resumo_horarios(agora=None):
    agora=agora or agora_local(); hs=HORARIOS["principal"]; primeiro,ultimo=hs[0],hs[-1]
    if agora.weekday()>=5:
        return f"🚌 <b>Circular UFRB — Principal</b>\n\nO Circular opera de segunda a sexta-feira.\n\n🕐 <b>Primeiro horário:</b> <b>{primeiro['hora']}</b>\n🌙 <b>Último horário:</b> <b>{ultimo['hora']}</b>"
    prox=proximo_horario(agora)
    if prox is None:
        return f"🚌 <b>Circular UFRB — Principal</b>\n\nAs viagens de hoje já encerraram.\n\n🕐 <b>Primeiro horário:</b> <b>{primeiro['hora']}</b>\n🌙 <b>Último horário:</b> <b>{ultimo['hora']}</b>"
    ic,nome=_periodo(agora); idx=hs.index(prox); proximas=hs[idx:idx+4]; linhas=["🚌 <b>Circular UFRB — Principal</b>",f"{ic} <b>Próximos horários — {nome}</b>",""]
    for n,h in enumerate(proximas,1):
        if n==1:
            p=estimar_chegada_portao_1(h["hora"]); pico=" ⚠️ pico" if p["pico"] else ""
            linhas += ["🟢 <b>Próxima volta</b>",f"  {_frase_saida(h['origem'])}: <b>{h['hora']}</b>{pico}",f"  🚪 Chega no Portão 1: <b>{p['inicio']}–{p['fim']}</b>"]
        else: linhas += _volta(h,n)
        p=estimar_chegada_portao_1(h["hora"])
        if p["noturno"] and not p["pico"]: linhas.append("  🌙 À noite pode chegar antes da estimativa.")
        linhas.append("")
    linhas.append("⚠️ <b>Horários de pico</b> — Pode haver pequenos atrasos." if any(estimar_chegada_portao_1(h["hora"])["pico"] for h in proximas) else "ℹ️ Horários do Portão 1 são previsões e podem variar.")
    return "\n".join(linhas)

def listar_horarios_periodo(periodo):
    hs=[h for h in HORARIOS["principal"] if _pertence(h["hora"],periodo)]
    if not hs: return "📋 <b>Principal</b>\n\nNenhum horário cadastrado para este período."
    linhas=["🚌 <b>Circular UFRB — Principal</b>",TITULOS_PERIODOS.get(periodo,periodo.title()),""]
    for n,h in enumerate(hs,1): linhas += _volta(h,n)+[""]
    linhas.append("⚠️ <b>Horários de pico</b> — Pode haver pequenos atrasos." if any(estimar_chegada_portao_1(h["hora"])["pico"] for h in hs) else "ℹ️ Horários do Portão 1 são previsões e podem variar.")
    return "\n".join(linhas)

def montar_rota_atual():
    linhas=["🗺️ ROTA PRINCIPAL","","➡️ Saída em direção à Rua",""]
    for i,item in enumerate(ROTA):
        p=PONTOS[item["ponto_id"]]; nome=p["nome"]
        if item.get("opcional",p.get("opcional",False)): nome += " (opcional)"
        linhas.append(f"{i+1}. {nome}")
        if item["ponto_id"]=="ponto_externo_2": linhas += ["","⬅️ Retorno em direção ao RU",""]
    linhas += ["","ℹ️ Pontos opcionais só são atendidos quando houver desembarque."]
    return "\n".join(linhas)

def estado_vazio(): return {"ponto_anterior":None,"ponto_atual":None,"horario":None,"telegram_id":None,"resultado_rota":None,"historico":[]}

def _dt(s): return datetime.fromisoformat(s) if s else None

def _iso(d): return d.isoformat() if d else None

def _ocorrencias(pid): return [i for i,x in enumerate(ROTA) if x["ponto_id"]==pid]

def _proximo(ind):
    if ind+1>=len(ROTA): return None
    it=ROTA[ind+1]; p=PONTOS[it["ponto_id"]]; r={"id":p["id"],"nome":p["nome"],"opcional":it.get("opcional",p.get("opcional",False))}
    if r["opcional"]:
        j=ind+2
        while j<len(ROTA):
            a=ROTA[j]
            if not a.get("opcional",False):
                pa=PONTOS[a["ponto_id"]]; r["alternativa"]={"id":pa["id"],"nome":pa["nome"]}; break
            j+=1
    return r

def _analisar(a,b):
    if a not in PONTOS or b not in PONTOS: return None
    cand=[]
    for ia in _ocorrencias(a):
        for ib in _ocorrencias(b):
            if ib>ia: cand.append((ib-ia,ib))
    if not cand: return None
    _,ib=min(cand,key=lambda x:x[0]); it=ROTA[ib]
    return {"ponto_anterior":PONTOS[a]["nome"],"ponto_atual":PONTOS[b]["nome"],"ponto_atual_id":b,"indice_atual":ib,"sentido":it["sentido_apos"],"proximo":_proximo(ib)}

def _resultado_hist(hist,ponto):
    total=len(hist)
    for i in range(total-1,-1,-1):
        reg=hist[i]; ant=reg["ponto_id"]
        if ant==ponto: continue
        r=_analisar(ant,ponto)
        if r:
            r["base_historico"]={"ponto_id":ant,"horario":reg["horario"],"telegram_id":reg.get("telegram_id")}; r["ignorou_registro_incompativel"]=i!=total-1; return r
    return None

def _previsto(h,agora):
    hh,mm=map(int,h.split(":")); return agora.replace(hour=hh,minute=mm,second=0,microsecond=0)

def _ultima_saida_recente(agora):
    c=[]
    for v in HORARIOS["principal"]:
        p=_previsto(v["hora"],agora); d=agora-p
        if timedelta(0)<=d<=timedelta(minutes=JANELA_SAIDA_RECENTE_MINUTOS): c.append((p,v))
    if not c:return None
    p,v=max(c,key=lambda x:x[0]); return {"hora":v["hora"],"origem":v["origem"],"previsto":p}

def _pre_saida(agora):
    p=proximo_horario(agora)
    if not p or _nome_origem(p.get("origem", ""))!="Garagem": return None
    d=_previsto(p["hora"],agora)-agora
    return {"hora":p["hora"],"origem":p["origem"],"faltam_segundos":max(0,int(d.total_seconds()))} if timedelta(0)<d<=timedelta(minutes=JANELA_PRE_SAIDA_GARAGEM_MINUTOS) else None

def _tem_recente(estado,agora):
    h=_dt(estado.get("horario")); return bool(h and timedelta(0)<=agora-h<=timedelta(minutes=JANELA_CONFIRMACAO_RECENTE_MINUTOS))

def _quebra_recente(agora):
    hs=HORARIOS["principal"]; q=None
    for a,b in zip(hs,hs[1:]):
        if _minutos(b["hora"])-_minutos(a["hora"])>LIMITE_INTERVALO_BLOCO_MINUTOS:
            ini=_previsto(b["hora"],agora)
            if ini<=agora:q=ini
    return q

def _lacuna(agora):
    ag=aguardando_proxima_saida(agora)
    if not ag or not ag.get("proxima"): return False
    hs=HORARIOS["principal"]; ph=ag["proxima"]["hora"]
    for i,h in enumerate(hs):
        if h["hora"]==ph and i>0: return _minutos(ph)-_minutos(hs[i-1]["hora"])>LIMITE_INTERVALO_BLOCO_MINUTOS
    return False

def limpar_se_expirado(estado,agora):
    h=_dt(estado.get("horario"))
    if not h:return estado
    exp=h.date()!=agora.date(); q=_quebra_recente(agora)
    if q and h<q: exp=True
    if _lacuna(agora) and not _tem_recente(estado,agora): exp=True
    return estado_vazio() if exp else estado

def registrar_passagem(estado,ponto_id,telegram_id=None,agora=None):
    agora=agora or agora_local(); estado=limpar_se_expirado(estado,agora)
    if ponto_id not in PONTOS:return estado,{"aceito":False,"motivo":"ponto_invalido"}
    ag=aguardando_proxima_saida(agora); pre=_pre_saida(agora)
    if ag and not pre and not _tem_recente(estado,agora): return estado,{"aceito":False,"motivo":"fora_circulacao","origem":ag["origem"],"proxima":ag.get("proxima")}
    if estado.get("ponto_atual")==ponto_id:return estado,{"aceito":False,"motivo":"duplicado","ponto":PONTOS[ponto_id]["nome"]}
    anterior=estado.get("ponto_atual"); hist=estado.get("historico",[]); resultado=_resultado_hist(hist,ponto_id)
    if resultado is None and anterior: resultado=_analisar(anterior,ponto_id)
    novo={"ponto_anterior":anterior,"ponto_atual":ponto_id,"horario":_iso(agora),"telegram_id":telegram_id,"resultado_rota":resultado,"historico":hist+[{"ponto_id":ponto_id,"horario":_iso(agora),"telegram_id":telegram_id}]}
    novo["historico"]=novo["historico"][-MAX_HISTORICO_REGISTROS:]
    return novo,{"aceito":True,"primeiro_registro":anterior is None,"ponto":PONTOS[ponto_id]["nome"],"resultado_rota":resultado}

def _tempo(h,agora):
    if not h:return "horário desconhecido"
    s=max(0,int((agora-h).total_seconds()))
    if s<60:return "agora mesmo"
    m=s//60
    if m<60:return f"há {m} min"
    hh=m//60; rr=m%60; return f"há {hh}h" if rr==0 else f"há {hh}h {rr}min"

def _movimento(r):
    sentido=r.get("sentido"); prox=r.get("proximo"); seta="➡️" if sentido=="RUA" else "⬅️"; linhas=[]
    if prox is None:
        if r.get("ponto_atual_id")=="ru": return "🏁 Chegada ao RU / fim da volta confirmada.\n🚌 O ônibus pode estar concluindo a volta anterior ou aguardando/iniciando uma nova saída.\nℹ️ Não é possível afirmar o sentido apenas por esta confirmação; os horários podem sofrer atraso."
        return f"🏁 Fim do percurso cadastrado.\n{seta} Sentido: {sentido}"
    if prox["opcional"]:
        linhas=["⏭️ Próximo:",f"     📍 {prox['nome']} (se houver parada)"]
        if prox.get("alternativa"): linhas.append(f"     ↪️ Caso não pare: {prox['alternativa']['nome']}")
    else: linhas=["⏭️ Próximo:",f"     📍 {prox['nome']}"]
    linhas.append(f"{seta} Sentido: {sentido}"); return "\n".join(linhas)

def _retorno(ret,prox):
    l=["↩️ Percurso de retorno","🚌 Pelo horário, o ônibus provavelmente está no percurso de retorno.",f"⬅️ Sentido: {ret['origem']}","📍 O ônibus ainda segue atendendo pontos durante esse percurso."]
    if prox:l += ["","⏰ Próxima volta prevista:",f"     🕐 {prox['hora']} — {prox['origem']}"]
    l.append("ℹ️ Situação estimada pelo horário, não por confirmação de passagem."); return "\n".join(l)

def _aguardando(a):
    o=a["origem"]; l=[f"🅿️ Provavelmente na {o}" if o=="Garagem" else f"📍 Provavelmente no {o}","🚌 Pelo horário, o ônibus provavelmente já concluiu o percurso anterior."]
    if a.get("proxima"):l += ["","⏰ Próxima saída prevista:",f"     🕐 {a['proxima']['hora']} — {a['proxima']['origem']}"]
    l.append("ℹ️ Situação estimada pelo horário, sem confirmação recente de passagem."); return "\n".join(l)

def montar_localizacao(estado,agora=None):
    agora=agora or agora_local(); estado=limpar_se_expirado(estado,agora); atual=viagem_em_andamento(agora); ret=viagem_em_retorno(agora); ag=aguardando_proxima_saida(agora); prox=proximo_horario(agora)
    if not estado.get("ponto_atual"):
        pre=_pre_saida(agora)
        if pre:
            minutos=max(1,(pre["faltam_segundos"]+59)//60)
            return estado,(f"🟡 Janela de pré-saída ativa.\n\n"
                          f"⏰ Saída oficial: {pre['hora']} — Garagem\n"
                          f"⌛ Faltam aproximadamente {minutos} min.\n\n"
                          "🚌 Sem confirmação recente, o ônibus pode ainda estar na Garagem ou já ter iniciado o percurso.\n"
                          "📍 Uma confirmação de ponto agora tem prioridade sobre essa estimativa.\n\n"
                          "ℹ️ O horário oficial é uma referência e pode haver pequena antecipação ou atraso.")
        if atual:return estado,f"🚌 Há uma volta prevista em andamento.\n🕐 Saída oficial: {atual['hora']} — {atual['origem']}\n➡️ Sentido provável: RUA\n\nℹ️ Não há confirmação recente de passagem; o ônibus pode estar adiantado ou atrasado."
        if ret:return estado,_retorno(ret,prox)
        if ag:return estado,_aguardando(ag)
        sr=_ultima_saida_recente(agora)
        if sr:return estado,f"🚌 Uma saída oficial recente ainda pode estar em percurso por causa de atraso.\n🕐 Saída prevista: {sr['hora']} — {sr['origem']}\n➡️ O sentido e a posição exata dependem de uma confirmação de passagem.\n\nℹ️ O horário oficial é apenas referência; a volta pode estar atrasada."
        return estado,"🚌 Ainda não há confirmação de passagem nesta sessão.\n\nUse 📍 Informar ponto atual para registrar quando o ônibus passar por um ponto."
    h=_dt(estado.get("horario")); pid=estado["ponto_atual"]; nome=PONTOS[pid]["nome"]; r=estado.get("resultado_rota"); linhas=[f"📍 Última confirmação: {nome}",f"🕐 {_tempo(h,agora)} ({h.strftime('%H:%M:%S') if h else '--:--'})"]
    if ret and h:
        hh,mm=map(int,ret["inicio_retorno"].split(":")); inicio=h.replace(hour=hh,minute=mm,second=0,microsecond=0)
        if h<inicio: linhas += ["",_retorno(ret,prox)]; return estado,"\n".join(linhas)
    if h and pid in {"biblioteca","pavilhao_2"} and (r is None or r.get("sentido")=="RUA"):
        ini=h.replace(hour=10,minute=15,second=0,microsecond=0); fim=h.replace(hour=10,minute=20,second=59,microsecond=999999)
        if ini<=h<=fim: linhas += ["","⚠️ Possível atraso no Portão 1","🚪 Passagem esperada por volta de 10:20.",f"📍 O ônibus ainda foi confirmado em {nome}.","ℹ️ É uma estimativa, não uma confirmação de atraso."]
    if r: linhas += ["",_movimento(r)]
    else:
        sr=_ultima_saida_recente(h or agora)
        ocorr=_ocorrencias(pid); idx=next((i for i in ocorr if ROTA[i]["sentido_apos"]=="RUA"),None)
        if sr and idx is not None:
            pr=_proximo(idx); linhas += ["",f"🕐 A confirmação é compatível com uma saída oficial recente: {sr['hora']} — {sr['origem']}.","➡️ Sentido provável: RUA"]
            if pr:
                if pr["opcional"]:
                    linhas += ["⏭️ Próximo esperado:",f"     📍 {pr['nome']} (se houver parada)"]
                    if pr.get("alternativa"):linhas.append(f"     ↪️ Caso não pare: {pr['alternativa']['nome']}")
                else: linhas += ["⏭️ Próximo esperado:",f"     📍 {pr['nome']}"]
            linhas.append("ℹ️ O horário é apenas referência e pode haver atraso.")
        else: linhas += ["","ℹ️ Ainda preciso de outra confirmação em um ponto diferente","para estimar o sentido e o próximo ponto."]
    return estado,"\n".join(linhas)
