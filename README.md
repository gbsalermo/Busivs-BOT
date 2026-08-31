# BUSIVS BOT 🚌

Bot comunitário para acompanhar o Circular da UFRB — Campus Cruz das Almas pelo Telegram, combinando horários oficiais, rota e confirmações colaborativas.

> **Status em 31/08/2026:** funcional em produção com Cloudflare Workers, Telegram Webhook e Durable Object. A Etapa 0 de organização/documentação está concluída; a próxima etapa funcional é Analytics, precedida por uma validação operacional do engajamento proativo após as correções de 25/08.

## Objetivo

O BUSIVS reduz a incerteza de quem espera o circular sem depender, nesta fase, de aplicativo próprio ou GPS dedicado.

O sistema trabalha com:

```text
confirmações colaborativas
+ sequência da rota
+ contexto de volta/bloco
+ horários oficiais como referência
+ inferências controladas
```

Autoridade operacional:

```text
confirmação confiável > inferência pelo trajeto > horário
```

Horário é referência, não prova automática de posição.

## Recursos atuais

Usuários podem:

- consultar onde o Circular Principal foi visto por último;
- informar um ponto de passagem durante operação válida;
- consultar próximas referências e listar horários;
- visualizar a rota atual pela área de Ajuda;
- acompanhar o Micro quando estiver em operação;
- confirmar que o Micro está rodando;
- informar Principal e Micro separadamente;
- receber avisos operacionais;
- enviar feedback;
- responder a pedidos colaborativos de confirmação.

Administração possui controles adicionais para:

- escolher a volta de referência do bloco;
- corrigir ponto/sentido por controles administrativos;
- corrigir/gerenciar Micro;
- marcar Garagem / encerrar bloco;
- publicar e remover avisos.

Não existe, no fluxo de produção atual, autenticação obrigatória por e-mail institucional ou registro por NFC. Essas ideias pertencem ao planejamento inicial/histórico e não devem ser assumidas como implementadas.

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

### Blocos operacionais

A configuração oficial está em `cloudflare/src/dados.py`.

Blocos atuais:

```text
06:25–07:55
09:35–10:00
11:30–12:20
13:00–14:00
15:35–16:00
17:30–18:15
20:00–20:00  [experimental]
20:40–20:40
21:40–21:40
22:30–22:30
```

A saída das **20:00** é experimental e pode não ocorrer; o bot mantém essa informação explicitamente marcada.

## Micro-ônibus 🚐

O Micro é tratado como reforço e mantém estado separado do Principal.

Referências atualmente configuradas:

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

- somente em contexto operacional válido do Principal;
- primeiro lote ~5 min normal / ~10 min pico;
- segundo lote ~15 min normal / ~20 min pico;
- fallback individual do último autor pode ocorrer;
- até 20 usuários por lote;
- máximo de 2 lotes coletivos por volta;
- convite válido por 3 minutos;
- nova confirmação confiável reinicia a lacuna de silêncio.

Em 25/08/2026 foi identificado que o código de engajamento não estava sendo exposto pelo entrypoint configurado no Worker. A produção passou a apontar para `entry_engajamento_final.py`. A correção está no código; a validação real/controlada do fluxo pós-correção deve ser feita antes de avançar para Analytics.

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
- Wrangler / pywrangler
- Durable Objects
- SQLite no Durable Object
- Telegram Bot API
- Telegram Webhooks
- Git / GitHub

## Produção x legado local

```text
main
→ produção Cloudflare

cloudflare/
→ implementação efetiva de produção

src/
→ base histórica/local por polling; não é o runtime de produção

alpha / local
→ branches históricas ou de referência
```

Não corrigir somente `src/bot.py` esperando alterar a produção.

## Documentação oficial

Ordem recomendada para uma pessoa ou IA assumir o projeto:

1. [Guia de Continuidade para IA](docs/GUIA_CONTINUIDADE_IA.md) — handoff completo;
2. [Continuidade](CONTINUIDADE.md) — status curto e próximo trabalho;
3. [Dossiê Mestre](docs/DOSSIE_MESTRE_BUSIVS.md) — fonte de verdade de regras e decisões;
4. [Plano de Evolução](docs/PLANO_EVOLUCAO_BUSIVS.md) — etapas oficiais;
5. [Blocos Operacionais](docs/BLOCOS_OPERACIONAIS.md) — janelas e transições;
6. [Fluxo Telegram](docs/FLUXO_TELEGRAM.md) — UX efetiva;
7. [Arquitetura](docs/ARQUITETURA.md) — visão técnica;
8. [Setup](docs/SETUP_LOCAL.md) e [Cloudflare README](cloudflare/README.md) — execução e testes.

`docs/ROADMAP_BETA.md` é histórico e não deve orientar implementação atual.

## Estado de evolução

```text
ETAPA 0 — Limpeza da Casa + Dossiê Mestre
✅ concluída e incorporada à main

GATE OPERACIONAL
🟡 validar engajamento proativo pós-correção e criar regressão

ETAPA 1 — Fundação de Analytics
⬜ não iniciada
```

Objetivos da Etapa 1:

- usuários únicos;
- primeira/última interação;
- total de interações;
- consultas de localização;
- confirmações;
- eventos Principal/Micro;
- base para painel administrativo de estatísticas.

Analytics será observacional: falha de métrica não pode bloquear o funcionamento normal do bot.

## Direção futura de automação física

Para uma fase posterior, a direção conceitual escolhida é um modelo híbrido com dispositivo embarcado de baixo custo:

```text
ESP32 + GPS + Wi-Fi institucional + geofences
```

A ideia é combinar evidência automática com a colaboração existente, sem substituir de imediato o modelo humano.

## Autor

**Gabriel Salermo**  
BCET / Engenharia da Computação — UFRB

---

> **BUSIVS — informação colaborativa para reduzir a incerteza de quem está esperando o circular.**
