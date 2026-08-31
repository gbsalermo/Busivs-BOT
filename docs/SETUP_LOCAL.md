# Setup e desenvolvimento local — BUSIVS BOT

> Revisado em 31/08/2026. A referência de produção é a implementação em `cloudflare/`. O antigo `src/bot.py` por polling é legado local/histórico.

## 1. Clonar a produção atual

```bash
git clone https://github.com/gbsalermo/Busivs-BOT.git
cd Busivs-BOT
git checkout main
```

Antes de trabalhar, leia:

```text
docs/GUIA_CONTINUIDADE_IA.md
CONTINUIDADE.md
docs/DOSSIE_MESTRE_BUSIVS.md
```

---

## 2. Requisitos da implementação Cloudflare

A pasta `cloudflare/` declara:

```text
Python >= 3.11
workers-py
```

Para o fluxo atual de desenvolvimento/deploy também são usados:

- `uv`;
- Node.js/Wrangler conforme o ambiente Cloudflare.

Entre na pasta:

```bash
cd cloudflare
```

Sincronize o ambiente:

```bash
uv sync
```

---

## 3. Secrets

Produção espera:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
ADMIN_TELEGRAM_ID
```

Nunca grave valores reais no Git.

Para configurar secrets no ambiente Cloudflare autorizado:

```bash
uv run pywrangler secret put TELEGRAM_BOT_TOKEN
uv run pywrangler secret put TELEGRAM_WEBHOOK_SECRET
uv run pywrangler secret put ADMIN_TELEGRAM_ID
```

A configuração estrutural do Worker fica em:

```text
cloudflare/wrangler.jsonc
```

---

## 4. Executar Worker localmente

Dentro de `cloudflare/`:

```bash
uv run pywrangler dev
```

O endpoint de saúde é:

```text
GET /health
```

Exemplo local padrão do Wrangler:

```bash
curl http://localhost:8787/health
```

O endpoint do Telegram é:

```text
POST /telegram/webhook
```

Ele exige o header secreto do Telegram. Não conecte o webhook real a uma instância local sem saber exatamente qual ambiente deve receber os updates.

---

## 5. Testes relevantes para produção

A suíte mais diretamente ligada às regras atuais está em:

```text
cloudflare/tests/
```

Ela usa `unittest` e cada teste adiciona `cloudflare/src` ao caminho quando necessário.

A partir da raiz do repositório:

```bash
python -m unittest discover -s cloudflare/tests -p "test_*.py"
```

Ou, com o ambiente `uv` da pasta Cloudflare, execute os testes usando o Python desse ambiente.

Os arquivos em:

```text
tests/
```

pertencem à base histórica/local e não devem ser tratados sozinhos como validação da produção.

### Gate atual

Antes da Etapa 1, falta adicionar/validar cobertura do engajamento proativo completo:

```text
cron
-> candidatos
-> convite
-> resposta/expiração
```

---

## 6. Deploy

Dentro de `cloudflare/`:

```bash
uv run pywrangler deploy
```

O `wrangler.jsonc` deve continuar apontando para:

```text
src/entry_engajamento_final.py
```

Não trocar o entrypoint sem revisar a cadeia funcional e validar cron, webhook e Durable Object.

Após deploy, conferir pelo menos:

1. `/health`;
2. webhook do Telegram;
3. `/start` e menu;
4. `Onde está o ônibus?`;
5. registro de ponto em janela válida;
6. Principal e Micro separados;
7. estado persistente no Durable Object;
8. controles administrativos;
9. cron/engajamento quando a mudança tocar esse fluxo.

---

## 7. Webhook

A produção possui endpoints administrativos para configurar/remover o webhook:

```text
POST /admin/telegram/set-webhook
POST /admin/telegram/delete-webhook
```

Esses endpoints exigem autenticação administrativa prevista no Worker.

O Telegram não entrega updates simultaneamente via webhook e `getUpdates`. Por isso, não misture o runtime atual com o antigo bot por polling sem remover/configurar conscientemente o webhook.

---

## 8. Base histórica por polling

A raiz ainda possui:

```text
src/
requirements.txt
.env.example
```

Esses arquivos representam a evolução inicial/local do bot.

Não use instruções antigas como:

```text
git checkout feat/python-base
python src/bot.py
```

como procedimento para desenvolver ou validar a produção atual.

Se o objetivo for investigar comportamento histórico, deixe isso explícito e não confunda resultados com o Worker Cloudflare.

---

## 9. Segurança antes de alterar produção

Arquivos de alta sensibilidade:

```text
cloudflare/wrangler.jsonc
cloudflare/src/entry_engajamento_final.py
cloudflare/src/estado_bus.py
cloudflare/src/dados.py
cloudflare/src/volta_referencia.py
cloudflare/src/blocos_operacionais.py
```

Mudanças no Durable Object/storage podem afetar estado persistido já existente.

Antes de refatorar uma camada `entry_*`:

```text
mapear dependências
-> criar regressão
-> alterar
-> testar
-> validar integração Cloudflare/Telegram
```

---

## 10. Dívida de ambiente

A `.venv` chegou a ser versionada no repositório. O `.gitignore` já foi reforçado, mas a remoção dos arquivos rastreados deve ser feita em uma operação Git dedicada, por exemplo com remoção do índice, sem misturar isso a mudança funcional.
