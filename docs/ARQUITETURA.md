# Arquitetura — BUSIVS BOT

> Visão técnica resumida da arquitetura efetiva em produção. Para regras completas e decisões que não devem ser revertidas, consulte `DOSSIE_MESTRE_BUSIVS.md`.

## 1. Visão geral

O BUSIVS é um bot Telegram executado em Cloudflare Workers para Python. O estado operacional é compartilhado por Durable Object com storage SQLite.

```text
Usuário
  ↓
Telegram Bot
  ↓ webhook HTTPS
Cloudflare Worker (Python)
  ↓
Entrypoint final
  ↓
Camadas de regras BUSIVS
  ↕
Durable Object / SQLite
  ↓
Telegram Bot API
```

O sistema não possui GPS nativo. A posição é inferida principalmente por confirmações colaborativas e sequência da rota.

Autoridade operacional:

```text
confirmação confiável > inferência pelo trajeto > horário
```

---

## 2. Camada externa — Cloudflare

Configuração:

```text
cloudflare/wrangler.jsonc
```

Produção auditada em 28/08/2026:

```text
name: busivs-bot
main: src/entry_engajamento_final.py
compatibility_flags: python_workers
cron: * * * * *
Durable Object binding: BUS_STATE
class_name: BusState
storage: sqlite
```

O cron existe para tarefas proativas, principalmente pedidos colaborativos de confirmação.

Secrets esperados:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
ADMIN_TELEGRAM_ID
```

---

## 3. Camada interna — Python

Entrypoint efetivo:

```text
entry_engajamento_final.py
```

Cadeia principal observada:

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

Essa representação mostra a cadeia de herança principal. Existem imports auxiliares entre módulos; por isso, nenhuma remoção deve ser feita apenas olhando o nome do arquivo.

### Funções das camadas mais sensíveis

`entry_engajamento_final.py`
: camada final atualmente exposta ao Cloudflare; garante que engajamento e cron convivam com a cadeia final de consistência.

`entry_consistencia.py`
: ajustes finais de coerência de Principal/Micro e exibição.

`entry_antiteleporte.py`
: tratamento de saltos suspeitos, estado não confiável e resolução por evidência posterior.

`entry_admin_hub.py`
: centralização dos controles administrativos e ajustes de apresentação.

`entry_core.py`
: Worker base, Telegram, menus e fluxo principal.

---

## 4. Domínio operacional

### Principal

Estado, rota e referência de volta são independentes de uma simples leitura do relógio. Horário serve como referência, não como prova automática de posição.

### Micro

Possui estado separado e regras de ativação/referência próprias, mantendo a mesma filosofia colaborativa do Principal.

### Biblioteca

É ponto ambíguo por aparecer na ida e no retorno. O sentido depende do contexto da rota e do estado confiável.

### Fim de bloco

O relógio pode encerrar o contexto quando o bloco realmente termina, evitando que uma volta antiga invada a próxima janela operacional.

---

## 5. Persistência

O Durable Object é parte da arquitetura de negócio, não apenas infraestrutura.

Dados operacionais persistentes incluem estados de localização, referências, sessões e controles de engajamento.

Alterações em:

```text
BusState
chaves de storage
formato JSON persistido
binding BUS_STATE
class_name do Durable Object
```

devem ser tratadas como mudanças potencialmente incompatíveis com produção.

---

## 6. Arquivos de domínio

```text
cloudflare/src/dados.py
```
Horários, pontos, blocos e rota.

```text
cloudflare/src/volta_referencia.py
```
Referência persistente de volta.

```text
cloudflare/src/registro_colaborativo.py
```
Sequência de rota sem depender do relógio do Principal.

```text
cloudflare/src/expiracao_volta.py
```
Fechamento real do contexto operacional.

```text
cloudflare/src/micro.py
cloudflare/src/entry_micro_flex.py
```
Operação e sessão do Micro.

```text
cloudflare/src/estado_bus.py
```
Estado base e helpers históricos. Antes de reutilizar uma função antiga, confirmar se a camada final ainda depende daquele comportamento.

---

## 7. Desenvolvimento local x produção

Branches históricas:

```text
main  -> produção Cloudflare
alpha -> testes locais / polling
local -> referência histórica
```

A existência de implementação local não significa que ela seja equivalente à produção. A camada Cloudflare possui webhook, Durable Object, cron e entrypoint próprios.

Toda mudança de regra deve ser verificada em dois níveis:

1. regra interna Python;
2. integração externa Cloudflare/Telegram.

---

## 8. Política de refatoração

O projeto cresceu por composição de camadas `entry_*`. Isso gera dívida técnica, mas também preserva comportamentos construídos incrementalmente.

Antes de consolidar ou remover uma camada:

1. mapear imports e herança;
2. identificar regra de negócio coberta;
3. criar teste de regressão;
4. validar Principal, Micro, administração, webhook e cron;
5. só então remover/consolidar.

A Etapa 0 não autoriza remoção agressiva de código de produção.

---

## 9. Documentos relacionados

- `docs/DOSSIE_MESTRE_BUSIVS.md` — fonte de verdade completa;
- `CONTINUIDADE.md` — status e próxima etapa;
- `docs/PLANO_EVOLUCAO_BUSIVS.md` — evolução planejada;
- `docs/BLOCOS_OPERACIONAIS.md` — detalhes de blocos;
- `docs/FLUXO_TELEGRAM.md` — experiência do bot.
