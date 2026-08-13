from collections import defaultdict, deque
from datetime import timedelta


# Valores iniciais propositalmente conservadores para teste na alpha.
# A ideia e bloquear apenas comportamento claramente anormal sem atrapalhar
# um aluno que faz uma confirmacao normal.
JANELA_PONTO_SEGUNDOS = 12
JANELA_USUARIO_SEGUNDOS = 20
MAX_TENTATIVAS_USUARIO = 4
INTERVALO_MINIMO_SEGUNDOS = 2
COOLDOWN_SEGUNDOS = 120
JANELA_CONFLITO_SEGUNDOS = 15
MAX_PONTOS_DISTINTOS = 3


class SegurancaColaborativa:
    """Protecoes temporarias para confirmacoes colaborativas.

    Nada aqui cria perfil permanente. Todos os dados ficam apenas em memoria e
    desaparecem quando o bot local e reiniciado. Na futura versao Cloudflare,
    a mesma ideia pode ser adaptada para armazenamento temporario no Durable
    Object.
    """

    def __init__(self):
        self._tentativas = defaultdict(deque)
        self._ultimas_por_usuario = {}
        self._cooldown_ate = {}
        self._ultima_confirmacao_ponto = {}

    def _limpar_usuario(self, uid, agora):
        limite = agora - timedelta(seconds=JANELA_USUARIO_SEGUNDOS)
        fila = self._tentativas[uid]
        while fila and fila[0][0] < limite:
            fila.popleft()

        cooldown = self._cooldown_ate.get(uid)
        if cooldown is not None and agora >= cooldown:
            self._cooldown_ate.pop(uid, None)

    def _bloquear(self, uid, agora, motivo):
        ate = agora + timedelta(seconds=COOLDOWN_SEGUNDOS)
        self._cooldown_ate[uid] = ate
        return {
            "permitido": False,
            "motivo": motivo,
            "aguarde_segundos": COOLDOWN_SEGUNDOS,
        }

    def verificar(self, uid, veiculo, ponto, agora):
        if uid is None:
            return {"permitido": True}

        uid = str(uid)
        self._limpar_usuario(uid, agora)

        cooldown = self._cooldown_ate.get(uid)
        if cooldown is not None and agora < cooldown:
            restante = max(1, int((cooldown - agora).total_seconds()))
            return {
                "permitido": False,
                "motivo": "cooldown",
                "aguarde_segundos": restante,
            }

        ultima_usuario = self._ultimas_por_usuario.get(uid)
        if ultima_usuario is not None:
            decorrido = (agora - ultima_usuario).total_seconds()
            if decorrido < INTERVALO_MINIMO_SEGUNDOS:
                return {
                    "permitido": False,
                    "motivo": "rapido_demais",
                    "aguarde_segundos": max(1, int(INTERVALO_MINIMO_SEGUNDOS - decorrido)),
                }

        chave_ponto = (veiculo, ponto)
        ultima_ponto = self._ultima_confirmacao_ponto.get(chave_ponto)
        if ultima_ponto is not None:
            decorrido = (agora - ultima_ponto).total_seconds()
            if decorrido < JANELA_PONTO_SEGUNDOS:
                # Confirmações equivalentes recentes nao precisam reescrever o
                # estado. Tambem nao contam como abuso do usuario.
                return {
                    "permitido": False,
                    "motivo": "ponto_ja_confirmado",
                    "aguarde_segundos": max(1, int(JANELA_PONTO_SEGUNDOS - decorrido)),
                }

        fila = self._tentativas[uid]
        fila.append((agora, veiculo, ponto))
        self._ultimas_por_usuario[uid] = agora

        if len(fila) > MAX_TENTATIVAS_USUARIO:
            return self._bloquear(uid, agora, "muitas_tentativas")

        limite_conflito = agora - timedelta(seconds=JANELA_CONFLITO_SEGUNDOS)
        pontos_recentes = {
            (v, p)
            for instante, v, p in fila
            if instante >= limite_conflito
        }
        if len(pontos_recentes) >= MAX_PONTOS_DISTINTOS:
            return self._bloquear(uid, agora, "conflito_usuario")

        return {"permitido": True}

    def registrar_confirmacao(self, veiculo, ponto, agora):
        self._ultima_confirmacao_ponto[(veiculo, ponto)] = agora

    def resumo(self):
        return {
            "usuarios_monitorados": len(self._tentativas),
            "usuarios_em_cooldown": len(self._cooldown_ate),
            "pontos_recentes": len(self._ultima_confirmacao_ponto),
        }
