# Arquitetura — BUSIVS BOT

> Visão técnica resumida da arquitetura efetiva em produção. Revisada em 31/08/2026. Para regras de negócio e decisões permanentes, consulte `DOSSIE_MESTRE_BUSIVS.md`.

## 1. Visão geral

O BUSIVS é um bot Telegram executado em Cloudflare Workers for Python. O estado operacional é compartilhado por Durable Object com storage SQLite.

```text
Usuário
  ↓
Telegram Bot
  ↓ webhook HTTPS
Cloudflare Worker (Python)
  ↓
entry_engajamento_final.py
  ↓
camadas de regras BUSIVS
  ↕
Durable Object / SQLite
  ↓
Telegram Bot API
```

O sistema não possui GPS nativo em produção. A posição é formada por confirmações colaborativas, sequência da rota, contexto da volta/bloco e horários usados como referência.

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

Produção atual:

```text
name: busivs-bot
main: src/entry_engajamento_final.py
compatibility_flags: python_workers
cron: * * * * *
Durable Object binding: BUS_STATE
class_name: BusState
storage: sqlite
```

O cron executa tarefas proativas, principalmente o mecanismo de engajamento colaborativo.

Secrets esperados:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
ADMIN_TELEGRAM_ID
```

Nunca versionar valores reais.

---

## 3. Camada interna — Python

Entrypoint efetivo:

```text
cloudflare/src/entry_engajamento_final.py
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

Essa representação mostra a cadeia principal de herança/composição. Existem imports auxiliares; portanto nenhuma remoção deve ser feita apenas olhando nomes de arquivos.

### Responsabilidades sensíveis

`entry_engajamento_final.py`
: camada exposta ao Worker; conecta a cadeia funcional final ao cron e às consultas candidatas ao engajamento.

`entry_consistencia.py`
: coerência final de Principal/Micro e apresentação.

`entry_antiteleporte.py`
: saltos suspeitos, estado não confiável e resolução por evidência posterior.

`entry_admin_hub.py`
: controles administrativos das camadas finais.

`entry.py`
: feedback, seleção administrativa de referência, Garagem e complementos de interface.

`entry_core.py`
: Worker base, Telegram, menus e handlers centrais.

---

## 4. Produção x legado local

```text
cloudflare/
= implementação de produção

src/
= implementação histórica/local por polling
```

A base em `src/` pode ser útil para referência e testes antigos, mas não é equivalente ao Worker atual.

Consequência prática:

```text
alterar src/bot.py
≠
alterar a produção Cloudflare
```

Documentação que ainda trate `src/bot.py` como aplicação principal deve ser considerada histórica/desatualizada.

---

## 5. Domínio operacional

### Principal

Estado, rota e referência de volta não são derivados de uma simples leitura do relógio. Horário serve como referência, não como prova automática de posição.

### Micro

Possui estado separado e regras próprias de sessão/referência, mantendo a mesma filosofia colaborativa.

### Biblioteca

É ponto ambíguo por aparecer na ida e no retorno. O sentido depende do contexto da rota e do estado confiável.

### Fim de bloco

O relógio pode encerrar o contexto quando o bloco realmente termina, evitando que uma volta antiga invada a próxima janela operacional.

### Garagem

É estado de encerramento/contexto operacional, não um ponto colaborativo comum da rota.

---

## 6. Persistência

O Durable Object é parte da arquitetura de negócio, não apenas infraestrutura.

Dados persistentes incluem estados de localização, referências, sessões, avisos e controles de engajamento.

Alterações em:

```text
BusState
chaves de storage
formatos persistidos
binding BUS_STATE
class_name do Durable Object
```

devem ser tratadas como potencialmente incompatíveis com produção.

---

## 7. Arquivos de domínio

```text
cloudflare/src/dados.py
```
Horários, pontos, blocos e rota. É a primeira fonte a consultar antes de alterar documentação operacional.

```text
cloudflare/src/blocos_operacionais.py
```
Regras compartilhadas de fechamento dos blocos.

```text
cloudflare/src/transicao_bloco.py
```
Transição limpa entre contexto antigo e novo bloco.

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
Operação, referência e sessão do Micro.

```text
cloudflare/src/estado_bus.py
```
Estado base e helpers históricos. Antes de reutilizar helper antigo, confirmar se a cadeia final ainda depende daquele comportamento.

---

## 8. Engajamento e cron

O cron roda a cada minuto.

A camada final registra usuários comuns que consultam `Onde está o ônibus?` e reutiliza a lógica de `entry_engajamento.py` para selecionar candidatos e enviar convites.

Produção sobrescreve o limite-base para:

```text
até 20 usuários por lote
```

Incidente conhecido de 25/08/2026: o Worker estava apontando para `entry_consistencia.py`, deixando a camada final de engajamento fora do entrypoint. O `wrangler.jsonc` foi corrigido para `entry_engajamento_final.py`.

O código está corrigido, mas o fluxo proativo deve ser validado de forma controlada e receber teste de regressão antes da Etapa 1.

---

## 9. Testes

```text
tests/
= base histórica/local

cloudflare/tests/
= cobertura mais diretamente relacionada à produção atual
```

Antes de refatorar camadas centrais, cobrir o comportamento que será movido/removido.

Lacuna conhecida: não há cobertura equivalente de ponta a ponta do fluxo completo de engajamento proativo (`cron -> candidatos -> convite -> resposta/expiração`).

---

## 10. Política de refatoração

O projeto cresceu por composição de camadas `entry_*`. Isso gera dívida técnica, mas também preserva comportamentos construídos incrementalmente.

Antes de consolidar/remover:

1. mapear imports e herança;
2. identificar regra de negócio coberta;
3. criar teste de regressão;
4. validar Principal, Micro, administração, webhook, cron e Durable Object;
5. só então remover/consolidar.

Não simplificar arquitetura sacrificando regra aprovada.

---

## 11. Documentos relacionados

- `docs/GUIA_CONTINUIDADE_IA.md` — handoff para outra IA;
- `CONTINUIDADE.md` — estado atual e próximo trabalho;
- `docs/DOSSIE_MESTRE_BUSIVS.md` — regras/decisões completas;
- `docs/PLANO_EVOLUCAO_BUSIVS.md` — roadmap oficial;
- `docs/BLOCOS_OPERACIONAIS.md` — blocos e transições;
- `docs/FLUXO_TELEGRAM.md` — experiência atual do bot;
- `cloudflare/README.md` — execução/deploy da produção.
