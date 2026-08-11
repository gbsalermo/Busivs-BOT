# BUSIVS BOT - Cloudflare Worker

Esta pasta contém a adaptação experimental do BUSIVS BOT para Cloudflare Workers.

A versão principal continua em `src/bot.py` usando polling. Nada nesta pasta deve substituir a versão atual até que o fluxo Cloudflare esteja validado.

## Etapa 6.1 - Worker HTTP mínimo ✅

Objetivo: provar que o projeto consegue executar como Python Worker antes de portar a lógica do Telegram.

Endpoints:

```text
GET  /health
POST /telegram/webhook
```

`/health` confirma que o Worker está executando.

## Etapa 6.2 - Webhook básico do Telegram 🚧

O endpoint `POST /telegram/webhook` agora:

1. valida o header `X-Telegram-Bot-Api-Secret-Token`;
2. lê o JSON do `Update` enviado pelo Telegram;
3. reconhece mensagens comuns;
4. extrai `chat.id` e texto;
5. envia uma resposta simples diretamente pela Telegram Bot API;
6. ainda não processa callbacks, menus ou regras completas do BUSIVS.

### Secrets necessárias

Nunca grave esses valores no repositório:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
```

Depois de autenticar o Wrangler na sua conta Cloudflare, configure:

```bash
cd cloudflare
uv run pywrangler secret put TELEGRAM_BOT_TOKEN
uv run pywrangler secret put TELEGRAM_WEBHOOK_SECRET
```

O `TELEGRAM_WEBHOOK_SECRET` deve ser um valor criado por nós e enviado também ao Telegram no `setWebhook`.

### Desenvolvimento local

Pré-requisitos:

- Node.js;
- `uv`;
- conta Cloudflare.

Dentro da pasta `cloudflare`:

```bash
uv sync
uv run pywrangler dev
```

Teste de saúde:

```bash
curl http://localhost:8787/health
```

O webhook pode ser testado localmente com um POST manual e o header secreto, sem registrar ainda o webhook real no Telegram.

### Deploy

Depois do teste local:

```bash
uv run pywrangler deploy
```

Primeiro teste a URL pública em:

```text
https://<worker>.workers.dev/health
```

Somente depois de `/health` responder corretamente devemos registrar:

```text
https://<worker>.workers.dev/telegram/webhook
```

como webhook do Telegram.

## Regra de segurança

Não ativar `setWebhook` enquanto o Worker não estiver publicado e validado. Enquanto um webhook estiver configurado, o Telegram não entrega updates via `getUpdates`, então o bot atual em polling deixa de receber mensagens.

Se precisarmos voltar ao bot local, devemos remover o webhook antes de iniciar novamente o polling.

## Próximo passo

Etapa 6.3: portar a interface do Telegram — `/start`, botões, callbacks e mensagens — sem ainda migrar o estado colaborativo para Durable Objects.
