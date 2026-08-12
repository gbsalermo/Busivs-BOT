import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_ESTADO = BASE_DIR / "estado_teste.json"
MAX_AVISOS_ATIVOS = 3
MAX_TAMANHO_AVISO = 280


class EstadoLocal:
    def __init__(self):
        self.dados = {
            "estado": None,
            "avisos": [],
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

    def obter_estado(self, estado_vazio):
        return self.dados.get("estado") or estado_vazio()

    def salvar_estado(self, estado):
        self.dados["estado"] = estado
        self._salvar()

    def listar_avisos(self):
        return list(self.dados.get("avisos", []))

    def adicionar_aviso(self, texto):
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
        avisos.append(texto)
        self.dados["avisos"] = avisos
        self._salvar()
        return {"ok": True, "duplicado": False, "avisos": avisos}

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
        self._salvar()
        return {"ok": True, "removido": removido, "avisos": avisos}

    def limpar_avisos(self):
        self.dados["avisos"] = []
        self.dados["aguardando_aviso_personalizado"] = False
        self._salvar()

    def iniciar_aviso_personalizado(self):
        self.dados["aguardando_aviso_personalizado"] = True
        self._salvar()

    def cancelar_aviso_personalizado(self):
        self.dados["aguardando_aviso_personalizado"] = False
        self._salvar()

    def aguardando_aviso_personalizado(self):
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
