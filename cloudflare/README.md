# BUSIVS BOT - Cloudflare Worker

Esta pasta contém a adaptação experimental do BUSIVS BOT para Cloudflare Workers.

A versão principal continua em `src/bot.py` usando polling. Nada nesta pasta deve substituir a versão atual até que o fluxo Cloudflare esteja validado.

## Etapa 6.1 - Worker HTTP mínimo

Objetivo: provar que o projeto consegue executar como Python Worker antes de portar a lógica do Telegram.

Estrutura inicial:

```text
cloudflare/
├── pyproject.toml
├── wrangler.jsonc
└── src/
    └── entry.py
```

Endpoints desta etapa:

```text
GET  /health
POST /telegram/webhook
```

`/health` confirma que o Worker está executando.

`/telegram/webhook` ainda retorna `501` de propósito. O webhook real só será ativado depois que a validação do Telegram, secrets e processamento básico estiverem implementados.

## Desenvolvimento local

Pré-requisitos para esta versão experimental:

- Node.js;
- `uv`;
- conta Cloudflare.

Dentro da pasta `cloudflare`:

```bash
uv sync
uv run pywrangler dev
```

Deploy, somente quando a etapa local estiver validada:

```bash
uv run pywrangler deploy
```

## Regra de segurança

Não configurar `setWebhook` no Telegram durante a Etapa 6.1. Enquanto um webhook estiver configurado, o Telegram não entrega updates via `getUpdates`, então o bot atual em polling deixaria de receber mensagens.

## Próximo passo

Etapa 6.2: receber um update de teste, validar o `X-Telegram-Bot-Api-Secret-Token` e preparar o envio de respostas pela Bot API sem ainda migrar o estado colaborativo.
