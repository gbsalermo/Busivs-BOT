import json
from datetime import datetime
from pathlib import Path

from avisos_blocos import expiracao_bloco_aviso
from regras import agora_local

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_ESTADO = BASE_DIR / "estado_teste.json"
MAX_AVISOS_ATIVOS = 3
MAX_TAMANHO_AVISO = 280


class EstadoLocal:
    def __init__(self):
        self.dados = {
            "estado": None,
            "avisos": [],
            "avisos_expiram_em": None,
            "aguardando_aviso_personalizado": False,
        }
        self._carregar()

    def _carregar(self):
        if not ARQUIVO_ESTADO.exists():
            return
        try:
            bruto = json.loads(ARQUIVO_ESTADO.read_text(encoding="utf-8"))
            if isinstance(bruto, dict):
                self.dados.update(bruto)
        except Exception:
            pass

    def _salvar(self):
        ARQUIVO_ESTADO.write_text(
            json.dumps(self.dados, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _expirar_avisos_se_necessario(self):
        expira_em = self.dados.get("avisos_expiram_em")
        if not expira_em:
            return
        try:
            expira_em = datetime.fromisoformat(expira_em)
        except Exception:
            self.dados["avisos"] = []
            self.dados["avisos_expiram_em"] = None
            self.dados["aguardando_aviso_personalizado"] = False
            self._salvar()
            return

        if agora_local() >= expira_em:
            self.dados["avisos"] = []
            self.dados["avisos_expiram_em"] = None
            self.dados["aguardando_aviso_personalizado"] = False
            self._salvar()

    def obter_estado(self, estado_vazio):
        return self.dados.get("estado") or estado_vazio()

    def salvar_estado(self, estado):
        self.dados["estado"] = estado
        self._salvar()

    def listar_avisos(self):
        self._expirar_avisos_se_necessario()
        return list(self.dados.get("avisos", []))

    def adicionar_aviso(self, texto):
        self._expirar_avisos_se_necessario()
        texto = (texto or "").strip()
        avisos = self.listar_avisos()
        if not texto:
            return {"ok": False, "motivo": "aviso_vazio", "avisos": avisos}
        if len(texto) > MAX_TAMANHO_AVISO:
            return {"ok": False, "motivo": "aviso_muito_longo", "avisos": avisos}
        if texto in avisos:
            return {"ok": True, "duplicado": True, "avisos": avisos}
        if len(avisos) >= MAX_AVISOS_ATIVOS:
            return {"ok": False, "motivo": "limite_atingido", "avisos": avisos}

        agora = agora_local()
        avisos.append(texto)
        self.dados["avisos"] = avisos
        if not self.dados.get("avisos_expiram_em"):
            self.dados["avisos_expiram_em"] = expiracao_bloco_aviso(agora).isoformat()
        self._salvar()
        return {
            "ok": True,
            "duplicado": False,
            "avisos": avisos,
            "expiram_em": self.dados.get("avisos_expiram_em"),
        }

    def remover_aviso(self, indice):
        avisos = self.listar_avisos()
        try:
            indice = int(indice)
        except Exception:
            return {"ok": False, "avisos": avisos}
        if indice < 0 or indice >= len(avisos):
            return {"ok": False, "avisos": avisos}
        removido = avisos.pop(indice)
        self.dados["avisos"] = avisos
        if not avisos:
            self.dados["avisos_expiram_em"] = None
        self._salvar()
        return {"ok": True, "removido": removido, "avisos": avisos}

    def limpar_avisos(self):
        self.dados["avisos"] = []
        self.dados["avisos_expiram_em"] = None
        self.dados["aguardando_aviso_personalizado"] = False
        self._salvar()

    def iniciar_aviso_personalizado(self):
        self._expirar_avisos_se_necessario()
        self.dados["aguardando_aviso_personalizado"] = True
        self._salvar()

    def cancelar_aviso_personalizado(self):
        self.dados["aguardando_aviso_personalizado"] = False
        self._salvar()

    def aguardando_aviso_personalizado(self):
        self._expirar_avisos_se_necessario()
        return bool(self.dados.get("aguardando_aviso_personalizado"))

    def salvar_aviso_personalizado(self, texto):
        resultado = self.adicionar_aviso(texto)
        if resultado.get("ok"):
            self.dados["aguardando_aviso_personalizado"] = False
            self._salvar()
        return resultado

    def limpar_estado(self, estado_vazio):
        self.dados["estado"] = estado_vazio()
        self._salvar()
