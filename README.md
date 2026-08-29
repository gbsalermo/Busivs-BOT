# BUSIVS BOT 🚌

Bot comunitário para acompanhar o Circular da UFRB — Campus Cruz das Almas pelo Telegram, combinando horários oficiais, rota e confirmações colaborativas.

> **Status:** funcional em produção com Cloudflare Workers, Telegram Webhook e Durable Object.

## Objetivo

O BUSIVS reduz a incerteza de quem espera o circular sem depender de aplicativo próprio ou GPS dedicado.

O sistema trabalha com:

```text
confirmações colaborativas
+ sequência da rota
+ contexto de volta/bloco
+ horários oficiais como referência
```

Autoridade operacional:

```text
confirmação confiável > inferência pelo trajeto > horário
```

Horário é referência, não prova automática de posição.

## Recursos atuais

Usuários podem:

- consultar onde o Circular Principal foi visto por último;
- informar um ponto de passagem;
- consultar próximas referências e horários;
- visualizar a rota;
- acompanhar o Micro quando estiver em operação;
- informar Principal e Micro separadamente;
- receber avisos operacionais;
- enviar feedback;
- responder a pedidos colaborativos de confirmação.

Administração possui controles adicionais para:

- escolher volta de referência;
- corrigir ponto/sentido;
- corrigir Micro;
- encerrar bloco / Garagem;
- publicar avisos.

## Circular Principal

Rota conceitual:

```text
RU / Residências
→ Fitotecnia
→ Solos / NEAS / Eng. Florestal
→ Pavilhão I
→ Biblioteca
→ Pavilhão II
→ Pavilhão de Engenharia (opcional)
→ Portão 2
→ Alex
→ Canaã
→ Portão 1
→ Biblioteca
→ Torre / COTEC (opcional)
→ RU / Residências
```

A Biblioteca aparece na ida e no retorno, então o sentido depende do contexto da rota e do estado confiável.

## Micro-ônibus 🚐

O Micro é tratado como reforço e mantém estado separado do Principal.

Referências atualmente documentadas:

```text
MANHÃ
07:25 — Garagem
07:40 — RU / Residências
07:55 — RU / Residências

MEIO-DIA
11:20 — Garagem
11:55 — RU / Residências
12:20 — RU / Residências
```

A lógica do Micro não deve avançar referência somente pelo relógio.

## Engajamento colaborativo

Quando há silêncio de confirmação, o BUSIVS pode perguntar a usuários que consultaram `Onde está o ônibus?` se viram o circular recentemente.

Regras principais:

- somente em contexto operacional válido;
- até 20 usuários por lote;
- máximo de 2 lotes coletivos por volta;
- convite válido por 3 minutos;
- nova confirmação confiável reinicia a lacuna de silêncio;
- horários de pico usam janelas maiores.

## Arquitetura

```text
Usuário
  ↓
Telegram
  ↓ webhook HTTPS
Cloudflare Worker — Python
  ↓
entry_engajamento_final.py
  ↓
camadas de regras BUSIVS
  ↕
Durable Object / SQLite
  ↓
Telegram Bot API
```

Produção é configurada em:

```text
cloudflare/wrangler.jsonc
```

Entrypoint efetivo:

```text
cloudflare/src/entry_engajamento_final.py
```

Cron atual:

```text
* * * * *
```

## Tecnologias

- Python
- Cloudflare Workers for Python
- Wrangler
- Durable Objects
- SQLite no Durable Object
- Telegram Bot API
- Telegram Webhooks
- Git / GitHub

## Branches

```text
main
→ produção Cloudflare

alpha
→ testes locais / polling

local
→ referência histórica
```

Branch atual da Etapa 0:

```text
chore/etapa-0-limpeza-dossie
```

## Documentação oficial

Ordem recomendada:

1. [Continuidade](CONTINUIDADE.md) — status atual e próxima etapa;
2. [Dossiê Mestre](docs/DOSSIE_MESTRE_BUSIVS.md) — fonte de verdade de arquitetura e regras;
3. [Plano de Evolução](docs/PLANO_EVOLUCAO_BUSIVS.md) — etapas futuras;
4. [Arquitetura](docs/ARQUITETURA.md) — visão técnica resumida;
5. [Blocos Operacionais](docs/BLOCOS_OPERACIONAIS.md);
6. [Fluxo Telegram](docs/FLUXO_TELEGRAM.md).

Documentos antigos como `ROADMAP_BETA.md` devem ser tratados como histórico, não como fonte de verdade atual.

## Estado de evolução

A fase funcional principal está operacional. O projeto entrou em melhoria contínua orientada por uso real.

Próxima etapa após a limpeza documental:

```text
ETAPA 1 — Fundação de Analytics
```

Objetivos iniciais:

- usuários únicos;
- interações;
- consultas de localização;
- confirmações;
- métricas por volta;
- efetividade dos avisos;
- painel administrativo de estatísticas.

Analytics será observacional: falha de métrica não pode bloquear o funcionamento normal do bot.

## Autor

**Gabriel Salermo**  
BCET / Engenharia da Computação — UFRB

---

> **BUSIVS — informação colaborativa para reduzir a incerteza de quem está esperando o circular.**
