import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

BASE_DIR = Path(__file__).resolve().parent.parent
CLOUDFLARE_SRC = BASE_DIR / "cloudflare" / "src"
sys.path.insert(0, str(CLOUDFLARE_SRC))
from dados import PONTOS, ROTULOS_PONTOS
from regras import agora_local, estado_vazio, listar_horarios_periodo, montar_localizacao, montar_resumo_horarios, montar_rota_atual, registrar_passagem
from validacao_rota import validar_deslocamento
from estado_local import EstadoLocal
from micro import resumo_micro
load_dotenv(BASE_DIR / ".env")
TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_TELEGRAM_ID=(os.getenv("ADMIN_TELEGRAM_ID") or "").strip()
if not TELEGRAM_BOT_TOKEN: raise RuntimeError("TELEGRAM_BOT_TOKEN nao configurado no .env")
ESTADO=EstadoLocal()
AVISOS_PREDEFINIDOS=["🚪 Portão 1 fechado","🚪 Portão 2 fechado","⚠️ Circular operando com atraso","🛠️ Circular temporariamente fora de operação","🛠️ Circular quebrou em meio ao trajeto","🌧️ Tempo chuvoso, circular pode demorar mais do que o esperado","🧍‍♂️🧍‍♀️ Superlotação do circular","🚌 Rota alterada temporariamente","📅 Horários especiais hoje"]
MANUAL="""📖 Dicas para uso do BUSIVS

🚌 Onde está o ônibus? — mostra a última confirmação colaborativa e a estimativa do trajeto.
📍 Informar ponto atual — use quando acabou de ver um veículo passar. Com o micro ativo, escolha primeiro qual veículo você viu.
⏰ Próximos horários — mostra a volta atual e próximas referências; com reforço ativo, inclui o micro.
📋 Listar horários — consulta os horários oficiais do circular principal por período.
🚐 Confirmar que micro está rodando — use somente quando realmente observar o micro de reforço operando. Qualquer usuário pode confirmar.
❓ Ajuda — permite consultar novamente este manual e a rota atual.

📢 Avisos operacionais ativos aparecem automaticamente no bot quando necessário.
❗ Localizações são colaborativas e horários são referências oficiais; atrasos podem acontecer.
🤝 Informe pontos apenas quando tiver visto o veículo. Isso melhora a informação para todos."""

def admin_ok(uid): return bool(ADMIN_TELEGRAM_ID and str(uid)==ADMIN_TELEGRAM_ID)
def limitar_resumo_principal(texto, quantidade=2):
 linhas=texto.splitlines(); marcador=f"<b>{quantidade+1}ª volta</b>"; inicio=next((i for i,l in enumerate(linhas) if marcador in l),None)
 if inicio is None:return texto
 rodape=next((i for i in range(inicio,len(linhas)) if linhas[i].startswith("⚠️ <b>Horários de pico</b>") or linhas[i].startswith("ℹ️ Horários do Portão 1")),None)
 if rodape is None:return "\n".join(linhas[:inicio]).rstrip()
 return "\n".join(linhas[:inicio]+linhas[rodape:]).strip()
def texto_tempo_micro():
 ativado_em=ESTADO.dados.get("micro_ativado_em")
 if not ativado_em:return ""
 try: inicio=datetime.fromisoformat(ativado_em); minutos=max(0,int((agora_local()-inicio).total_seconds()//60))
 except Exception:return ""
 if minutos<1:return "🕐 Operação confirmada agora."
 if minutos==1:return "🕐 Operação confirmada há 1 min."
 return f"🕐 Operação confirmada há {minutos} min."
def resumo_micro_status():
 status=texto_tempo_micro(); base=resumo_micro(); return base+("\n"+status if status else "")
def teclado_menu(uid=None):
 rotulo_micro="🚐 Micro em operação ✅" if ESTADO.micro_esta_ativo() else "🚐 Confirmar que micro está rodando"
 l=[[InlineKeyboardButton("🚌 Onde está o ônibus?",callback_data="onde")],[InlineKeyboardButton("📍 Informar ponto atual",callback_data="local")],[InlineKeyboardButton("⏰ Próximos horários",callback_data="horarios")],[InlineKeyboardButton("📋 Listar horários",callback_data="listar_horarios")],[InlineKeyboardButton(rotulo_micro,callback_data="micro_confirmar")]]
 if admin_ok(uid): l.append([InlineKeyboardButton("📢 Avisos",callback_data="avisos")])
 l.append([InlineKeyboardButton("❓ Ajuda",callback_data="ajuda")]); return InlineKeyboardMarkup(l)
def teclado_confirmar_micro(): return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Sim, está rodando",callback_data="micro_confirmar_sim")],[InlineKeyboardButton("❌ Voltar",callback_data="menu")]])
def teclado_voltar(): return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao menu",callback_data="menu")]])
def teclado_ajuda(): return InlineKeyboardMarkup([[InlineKeyboardButton("🗺️ Rota atual",callback_data="rota")],[InlineKeyboardButton("📖 Dicas para uso do BOT",callback_data="manual")],[InlineKeyboardButton("⬅️ Voltar ao menu",callback_data="menu")]])
def teclado_periodos(): return InlineKeyboardMarkup([[InlineKeyboardButton("🌅 Manhã",callback_data="periodo_manha"),InlineKeyboardButton("🍽️ Almoço",callback_data="periodo_meio_dia")],[InlineKeyboardButton("🌤️ Tarde",callback_data="periodo_tarde"),InlineKeyboardButton("🌙 Noite",callback_data="periodo_noite")],[InlineKeyboardButton("⬅️ Voltar ao menu",callback_data="menu")]])
def teclado_pontos(prefixo):
 b=[InlineKeyboardButton(ROTULOS_PONTOS.get(pid,p["nome"]),callback_data=f"{prefixo}_{pid}") for pid,p in PONTOS.items()]; l=[b[i:i+2] for i in range(0,len(b),2)]; l.append([InlineKeyboardButton("⬅️ Voltar ao menu",callback_data="menu")]); return InlineKeyboardMarkup(l)
def teclado_veiculo(): return InlineKeyboardMarkup([[InlineKeyboardButton("🚌 Circular principal",callback_data="veiculo_principal")],[InlineKeyboardButton("🚐 Micro — reforço",callback_data="veiculo_micro")],[InlineKeyboardButton("⬅️ Voltar ao menu",callback_data="menu")]])
def teclado_admin_avisos():
 l=[[InlineKeyboardButton(t,callback_data=f"aviso_add_{i}")] for i,t in enumerate(AVISOS_PREDEFINIDOS)]+[[InlineKeyboardButton("✏️ Aviso personalizado",callback_data="aviso_personalizado")],[InlineKeyboardButton("🗑️ Remover aviso",callback_data="aviso_remover_menu")],[InlineKeyboardButton("🧹 Limpar todos",callback_data="aviso_limpar")]]
 if ESTADO.micro_esta_ativo(): l.append([InlineKeyboardButton("🚐 Desativar micro",callback_data="micro_desativar")])
 l.append([InlineKeyboardButton("⬅️ Voltar ao menu",callback_data="menu")]); return InlineKeyboardMarkup(l)
def teclado_remover_avisos(a):
 l=[[InlineKeyboardButton("❌ "+t[:45],callback_data=f"aviso_rem_{i}")] for i,t in enumerate(a)]; l.append([InlineKeyboardButton("⬅️ Voltar aos avisos",callback_data="avisos")]); return InlineKeyboardMarkup(l)
def texto_avisos(a,c=False): return (f"📢 Avisos{' ('+str(len(a))+'/3)' if c else ''}\n\nNenhum aviso operacional ativo no momento." if not a else "\n".join([f"📢 Avisos ativos{' ('+str(len(a))+'/3)' if c else ''}",""]+[f"• {x}" for x in a]))
async def enviar_menu(m,uid=None):
 await m.reply_text("🚌 BUSIVS BOT — ALPHA LOCAL\n\nEscolha uma opção:",reply_markup=teclado_menu(uid)); a=ESTADO.listar_avisos()
 if a: await m.reply_text(texto_avisos(a))
async def start(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if u.effective_message: await u.effective_message.reply_text("👋 Bem-vindo ao BUSIVS!\n\n"+MANUAL); await enviar_menu(u.effective_message,u.effective_user.id if u.effective_user else None)
async def texto_admin(u:Update,c:ContextTypes.DEFAULT_TYPE):
 if not u.effective_message or not u.effective_user or not admin_ok(u.effective_user.id) or not ESTADO.aguardando_aviso_personalizado(): return
 t=(u.effective_message.text or "").strip()
 if t in {"/cancelar","/cancel"}: ESTADO.cancelar_aviso_personalizado(); await u.effective_message.reply_text("❌ Criação cancelada.",reply_markup=teclado_admin_avisos()); return
 r=ESTADO.salvar_aviso_personalizado(t); await u.effective_message.reply_text(("✅ Aviso publicado." if r.get("ok") else "⚠️ Não consegui publicar.")+"\n\n"+texto_avisos(r.get("avisos",[]),True),reply_markup=teclado_admin_avisos())
async def callback(u:Update,c:ContextTypes.DEFAULT_TYPE):
 q=u.callback_query; await q.answer(); a=q.data or ""; uid=u.effective_user.id if u.effective_user else None; m=q.message
 if a=="menu": await enviar_menu(m,uid); return
 if a=="ajuda": await m.reply_text("❓ Ajuda\n\nEscolha uma opção:",reply_markup=teclado_ajuda()); return
 if a=="manual": await m.reply_text(MANUAL,reply_markup=teclado_ajuda()); return
 if a=="rota": await m.reply_text(montar_rota_atual(),reply_markup=teclado_ajuda()); return
 if a=="micro_confirmar": await m.reply_text("🚐 Você viu o micro?",reply_markup=teclado_confirmar_micro()); return
 if a=="micro_confirmar_sim":
  r=ESTADO.ativar_micro(); t="🚐 Obrigado pela informação! O micro foi marcado como em operação." if not r.get("ja_ativo") else "🚐 O micro já estava marcado como em operação. Obrigado por confirmar!"; await m.reply_text(t+"\n\n"+resumo_micro_status(),parse_mode="HTML",reply_markup=teclado_voltar()); return
 if a=="micro_desativar":
  if admin_ok(uid): ESTADO.desativar_micro(); await m.reply_text("🚐 Micro desativado pelo administrador.",reply_markup=teclado_admin_avisos())
  return
 if a=="onde":
  e=ESTADO.obter_estado(estado_vazio); e,t=montar_localizacao(e); ESTADO.salvar_estado(e)
  if ESTADO.micro_esta_ativo(): em=ESTADO.obter_estado(estado_vazio,"micro"); em,tm=montar_localizacao(em); ESTADO.salvar_estado(em,"micro"); t+="\n\n🚐 MICRO — REFORÇO\n"+tm
  await m.reply_text(t,reply_markup=teclado_voltar()); return
 if a=="local":
  if ESTADO.micro_esta_ativo(): await m.reply_text("📍 Qual veículo você viu?",reply_markup=teclado_veiculo())
  else: await m.reply_text("📍 Onde o ônibus acabou de passar?",reply_markup=teclado_pontos("local_principal"))
  return
 if a=="veiculo_principal": await m.reply_text("🚌 Onde o circular acabou de passar?",reply_markup=teclado_pontos("local_principal")); return
 if a=="veiculo_micro": await m.reply_text("🚐 Onde o micro acabou de passar?",reply_markup=teclado_pontos("local_micro")); return
 if a.startswith("local_principal_") or a.startswith("local_micro_"):
  v="micro" if a.startswith("local_micro_") else "principal"; p=a.replace(f"local_{v}_","",1); e=ESTADO.obter_estado(estado_vazio,v); agora=agora_local(); bloqueio=validar_deslocamento(e,p,agora,ESTADO.listar_avisos()); r=bloqueio
  if r is None: e,r=registrar_passagem(e,p,uid,agora=agora); ESTADO.salvar_estado(e,v)
  t="Valeu! Registramos o ponto 😊" if r.get("aceito") else "Obrigado pela informação 😊" if r.get("motivo")=="duplicado" else "⚠️ Não foi possível registrar esta confirmação."
  await m.reply_text(t,reply_markup=teclado_voltar()); return
 if a=="horarios":
  micro_ativo=ESTADO.micro_esta_ativo(); t=montar_resumo_horarios()
  if micro_ativo: t=limitar_resumo_principal(t,2)+"\n\n"+resumo_micro_status()
  await m.reply_text(t,parse_mode="HTML",reply_markup=teclado_voltar()); return
 if a=="listar_horarios": await m.reply_text("📋 Qual período você quer consultar?",reply_markup=teclado_periodos()); return
 if a.startswith("periodo_"): await m.reply_text(listar_horarios_periodo(a.replace("periodo_","",1)),parse_mode="HTML",reply_markup=teclado_voltar()); return
 if a=="avisos":
  if not admin_ok(uid): return
  av=ESTADO.listar_avisos(); await m.reply_text(texto_avisos(av,True)+"\n\n🔐 Painel administrativo",reply_markup=teclado_admin_avisos()); return
 if a=="aviso_personalizado":
  if admin_ok(uid): ESTADO.iniciar_aviso_personalizado(); await m.reply_text("✏️ Envie a mensagem do aviso. Máximo 280 caracteres. /cancelar para sair.")
  return
 if a.startswith("aviso_add_"):
  if not admin_ok(uid): return
  try:t=AVISOS_PREDEFINIDOS[int(a.replace("aviso_add_","",1))]
  except:return
  r=ESTADO.adicionar_aviso(t); await m.reply_text(("✅ Aviso ativado." if r.get("ok") else "⚠️ Não foi possível ativar.")+"\n\n"+texto_avisos(r.get("avisos",[]),True),reply_markup=teclado_admin_avisos()); return
 if a=="aviso_remover_menu":
  if not admin_ok(uid): return
  av=ESTADO.listar_avisos(); await m.reply_text("🗑️ Escolha o aviso:" if av else "📢 Não há avisos ativos.",reply_markup=teclado_remover_avisos(av) if av else teclado_admin_avisos()); return
 if a.startswith("aviso_rem_"):
  if not admin_ok(uid): return
  r=ESTADO.remover_aviso(a.replace("aviso_rem_","",1)); await m.reply_text("✅ Aviso removido.\n\n"+texto_avisos(r.get("avisos",[]),True),reply_markup=teclado_admin_avisos()); return
 if a=="aviso_limpar":
  if admin_ok(uid): ESTADO.limpar_avisos(); await m.reply_text("🧹 Todos os avisos foram removidos.",reply_markup=teclado_admin_avisos())
def main():
 print("BUSIVS ALPHA LOCAL iniciado por polling."); app=Application.builder().token(TELEGRAM_BOT_TOKEN).build(); app.add_handler(CommandHandler("start",start)); app.add_handler(CallbackQueryHandler(callback)); app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,texto_admin)); app.run_polling(drop_pending_updates=True)
if __name__=="__main__": main()
