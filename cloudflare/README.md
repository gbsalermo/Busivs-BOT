# BUSIVS BOT — Cloudflare Worker

> Esta pasta contém a **implementação efetiva de produção** do BUSIVS. Revisado em 31/08/2026. A documentação antiga que tratava este Worker como experimental ficou obsoleta após a migração para webhook + Durable Object.

## 1. Arquitetura atual

```text
Telegram
  ↓ webhook HTTPS
Cloudflare Worker — Python
  ↓
src/entry_engajamento_final.py
  ↓
camadas de regras BUSIVS
  ↕
Durable Object BUS_STATE / SQLite
  ↓
Telegram Bot API
```

Configuração:

```text
wrangler.jsonc
```

Valores principais:

```text
name: busivs-bot
main: src/entry_engajamento_final.py
cron: * * * * *
BUS_STATE -> BusState
storage: sqlite
```

---

## 2. Entrypoint

Produção deve continuar entrando por:

```text
src/entry_engajamento_final.py
```

Essa camada mantém a cadeia final de consistência/antiteleporte e reintegra o engajamento colaborativo ao Worker e ao cron.

Cadeia principal:

```text
entry_engajamento_final
-> entry_consistencia
-> entry_antiteleporte
-> entry_admin_hub
-> entry_micro_admin
-> entry_micro_flex
-> entry_ultima_volta
-> entry_engajamento
-> entry_admin
-> entry
-> entry_core
```

Não trocar o entrypoint para uma camada intermediária apenas porque ela “parece mais simples”. Isso já causou perda do fluxo proativo de engajamento em 25/08/2026.

---

## 3. Endpoints

### Saúde

```text
GET /health
```

Usado para confirmar que o Worker está respondendo.

### Telegram

```text
POST /telegram/webhook
```

Valida o header:

```text
X-Telegram-Bot-Api-Secret-Token
```

antes de processar updates.

### Administração do webhook

```text
POST /admin/telegram/set-webhook
POST /admin/telegram/delete-webhook
```

Esses endpoints exigem autenticação administrativa prevista no Worker.

---

## 4. Secrets

Esperados em produção:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
ADMIN_TELEGRAM_ID
```

Nunca versionar valores reais.

Com ambiente Cloudflare autorizado:

```bash
uv run pywrangler secret put TELEGRAM_BOT_TOKEN
uv run pywrangler secret put TELEGRAM_WEBHOOK_SECRET
uv run pywrangler secret put ADMIN_TELEGRAM_ID
```

---

## 5. Desenvolvimento local

Pré-requisitos:

- Python >= 3.11;
- `uv`;
- Node.js/Wrangler conforme o ambiente Cloudflare.

Dentro de `cloudflare/`:

```bash
uv sync
uv run pywrangler dev
```

Teste de saúde:

```bash
curl http://localhost:8787/health
```

Não registre o webhook real contra um ambiente local sem intenção explícita, pois isso muda para onde o Telegram entrega os updates.

---

## 6. Testes

A suíte mais relacionada à produção está em:

```text
tests/
```

A partir da raiz do repositório, ela corresponde a:

```text
cloudflare/tests/
```

Exemplo:

```bash
python -m unittest discover -s cloudflare/tests -p "test_*.py"
```

Coberturas atuais incluem regras de rota, blocos, RU, referência de volta, retorno à Garagem e validações relacionadas.

Lacuna conhecida: o fluxo completo de engajamento proativo ainda precisa de regressão dedicada.

---

## 7. Deploy

```bash
uv run pywrangler deploy
```

Depois do deploy, validar:

```text
/health
Telegram webhook
/start e menu
Onde está o ônibus?
registro colaborativo
Principal x Micro
admin
Durable Object
cron quando aplicável
```

---

## 8. Cron e engajamento

O cron atual:

```text
* * * * *
```

executa a verificação do mecanismo proativo.

Em produção, `entry_engajamento_final.py` eleva o limite efetivo para:

```text
até 20 usuários por lote
```

Os convites expiram em 3 minutos e o máximo é de 2 lotes coletivos por volta.

### Incidente conhecido

Em 25/08/2026, o `wrangler.jsonc` ainda expunha `entry_consistencia.py`, então a lógica proativa não estava no entrypoint efetivo.

A correção alterou o `main` para:

```text
src/entry_engajamento_final.py
```

O código atual contém a correção. Antes de iniciar Analytics, validar o fluxo em cenário controlado e adicionar regressão para cron/candidatos/convites.

---

## 9. Durable Object

Binding:

```text
BUS_STATE
```

Classe:

```text
BusState
```

Storage:

```text
sqlite
```

O estado persistido faz parte do comportamento do produto. Não alterar nomes, chaves, formatos persistidos ou classe sem estratégia de compatibilidade.

---

## 10. Produção x polling antigo

O bot antigo em:

```text
../src/
```

usa a arquitetura local/histórica por polling e **não é a versão principal atual**.

Enquanto webhook estiver configurado, o Telegram não entrega os mesmos updates por `getUpdates`. Portanto, qualquer teste do legado por polling exige tratamento consciente do webhook e não deve ser feito como rotina de desenvolvimento de produção.

---

## 11. Documentação obrigatória

Antes de mudança relevante, leia:

```text
../docs/GUIA_CONTINUIDADE_IA.md
../CONTINUIDADE.md
../docs/DOSSIE_MESTRE_BUSIVS.md
../docs/PLANO_EVOLUCAO_BUSIVS.md
../docs/BLOCOS_OPERACIONAIS.md
```

Horários, pontos e blocos devem ser confirmados em:

```text
src/dados.py
```
