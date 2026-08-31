# Guia de Continuidade para IA — BUSIVS BOT

> Leia este arquivo primeiro ao assumir o projeto. Atualizado em 31/08/2026 após revisão cruzada da documentação, configuração Cloudflare, código de produção e histórico recente.

## 1. O que é o BUSIVS

O BUSIVS é um bot comunitário no Telegram para reduzir a incerteza sobre a posição e a operação do Circular da UFRB — Campus Cruz das Almas.

O produto atual **não usa GPS nativo**. A posição é formada por:

```text
confirmações colaborativas
+ sequência física da rota
+ contexto da volta/bloco
+ horários oficiais como referência
+ inferências controladas
```

Regra de autoridade:

```text
confirmação confiável > inferência pelo trajeto > horário
```

Nunca transforme horário em prova automática de posição.

---

## 2. Produção atual

A produção está na branch:

```text
main
```

Runtime:

```text
Cloudflare Workers for Python
Telegram Webhook
Durable Object + SQLite
Cron a cada minuto
```

Configuração externa:

```text
cloudflare/wrangler.jsonc
```

Entrypoint efetivo:

```text
cloudflare/src/entry_engajamento_final.py
```

Binding persistente:

```text
BUS_STATE -> BusState
```

Secrets esperados:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
ADMIN_TELEGRAM_ID
```

Nunca versionar valores reais.

---

## 3. O que NÃO é produção

A pasta raiz `src/` e o antigo fluxo por polling representam a base local/histórica do protótipo. Eles podem ser úteis como referência, mas **não são a implementação que atende o Telegram em produção**.

Não fazer uma correção em `src/bot.py` esperando alterar o Worker atual.

Também não assumir como implementados itens antigos de documentação, especialmente:

- autenticação por e-mail institucional;
- NFC/deep link por ponto;
- modo de férias automático.

Essas ideias apareceram em documentos iniciais, mas não fazem parte do fluxo de produção atual.

---

## 4. Cadeia funcional de produção

A cadeia principal observada é:

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

Existem imports auxiliares entre módulos. Não remover uma camada `entry_*` apenas porque existe outra mais nova.

Antes de consolidar/remover:

```text
mapear dependência
-> identificar regra fornecida
-> criar teste de regressão
-> validar Principal + Micro + admin + webhook + cron
-> só então remover
```

---

## 5. Regras de negócio que não podem ser quebradas

1. relógio sozinho não troca volta dentro do mesmo bloco;
2. o fim real do bloco pode encerrar contexto velho para impedir vazamento ao bloco seguinte;
3. RU confiável encerra a volta atual, mas não inicia a próxima sozinho;
4. uma nova volta pode ser reconhecida pela sequência real da rota quando houver saída oficial compatível;
5. Biblioteca aparece na ida e no retorno e exige contexto;
6. salto suspeito pede confirmação adicional e, se confirmado, vira indicação não confiável;
7. indicação não confiável não substitui a última posição confiável e não fecha/abre volta;
8. Principal e Micro possuem estados independentes;
9. a última volta segue em **percurso de retorno sentido Garagem**, sem sugerir que os pontos restantes deixaram de ser atendidos;
10. depois do encerramento real do bloco, a consulta deve indicar Garagem/próxima saída em vez de manter uma volta velha indefinidamente.

Detalhes: `docs/DOSSIE_MESTRE_BUSIVS.md` e `docs/BLOCOS_OPERACIONAIS.md`.

---

## 6. Estado funcional atual

### Usuário comum

Fluxos efetivos:

- `🚌 Onde está o ônibus?`;
- `📍 Informar ponto atual`, apenas quando Principal ou Micro está em operação;
- `⏰ Próximos horários`;
- `📋 Listar horários`;
- `🚐 Confirmar que o micro está rodando`;
- `❓ Ajuda`;
- rota atual dentro de Ajuda;
- envio de feedback dentro de Ajuda;
- resposta a convite colaborativo de confirmação.

Não existe cadastro/autenticação institucional obrigatória no fluxo atual.

### Administração

Além do fluxo comum, existem controles para:

- escolher a volta de referência do bloco;
- marcar Garagem / encerrar bloco;
- corrigir estado/ponto/sentido por controles administrativos das camadas finais;
- administrar o Micro;
- publicar/remover avisos operacionais.

---

## 7. Circular Principal e blocos

A configuração oficial fica em:

```text
cloudflare/src/dados.py
```

Os blocos atuais incluem:

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

A referência das **20:00** é experimental, baseada em rotina anterior, e pode não ocorrer. Não removê-la nem tratá-la como confirmada sem decisão explícita.

A fonte técnica dos fechamentos é `BLOCOS_PRINCIPAL` + regras de `blocos_operacionais.py`.

---

## 8. Micro-ônibus

O Micro é reforço e mantém estado separado do Principal.

Referências configuradas:

```text
07:25 — Garagem
07:40 — RU/Residências
07:55 — RU/Residências

11:20 — Garagem
11:55 — RU/Residências
12:20 — RU/Residências
```

Tempo desde a ativação não é prova de posição. A referência não deve avançar apenas pelo relógio.

---

## 9. Engajamento colaborativo

Objetivo: quando a localização fica sem confirmação, perguntar a quem consultou `Onde está o ônibus?` se viu o Circular.

Regra atual:

- somente em operação válida do Principal;
- usuários comuns que consultam localização entram como candidatos;
- primeiro lote: ~5 min em horário normal / ~10 min em pico;
- segundo lote: ~15 min normal / ~20 min pico;
- fallback individual do último autor pode ocorrer no meio do fluxo;
- até 20 usuários por lote em produção;
- máximo de 2 lotes coletivos por volta;
- convite válido por 3 minutos;
- confirmação confiável reinicia a lacuna de silêncio.

### Incidente conhecido de 25/08/2026

Foi observado em uso real que os avisos não estavam chegando. O código de engajamento existia, mas o `wrangler.jsonc` ainda apontava para `entry_consistencia.py`.

Correções realizadas:

```text
66ce4f3 — reintegra avisos colaborativos ao entrypoint final
020f09c — ativa entry_engajamento_final.py no Worker
2a14042 — aumenta lote efetivo para até 20 candidatos
```

Situação documental atual:

```text
correção presente no código
+ cron configurado a cada minuto
+ validação real pós-correção ainda deve ser tratada como gate operacional
```

Antes de iniciar Analytics, faça pelo menos um teste real/controlado de convite e crie teste de regressão para o cron/seleção de candidatos. Hoje a suíte Cloudflare cobre várias regras de rota/bloco, mas não possui cobertura equivalente do fluxo completo de engajamento proativo.

---

## 10. Etapas do projeto

```text
ETAPA 0 — Limpeza da Casa + Dossiê Mestre
STATUS: CONCLUÍDA e incorporada à main

GATE OPERACIONAL
STATUS: validar em produção o engajamento pós-correção e registrar regressão

ETAPA 1 — Fundação de Analytics
STATUS: NÃO INICIADA

ETAPA 2 — Painel Administrativo de Estatísticas
ETAPA 3 — Saúde das Voltas
ETAPA 4 — Efetividade dos Avisos Colaborativos
ETAPA 5 — Impacto da Colaboração
ETAPA 6 — Feedback Estruturado
ETAPA 7 — Comunicação Operacional
ETAPA 8 — Automação Física / Modelo Híbrido
```

Não renumerar ou criar um roadmap paralelo sem decisão explícita. O plano oficial está em `docs/PLANO_EVOLUCAO_BUSIVS.md`.

---

## 11. Direção já decidida para automação física

A direção conceitual preferida para a Etapa 8 é um dispositivo embarcado de baixo custo no ônibus, alimentado no próprio veículo, combinando:

```text
ESP32
+ GPS
+ Wi-Fi institucional
+ geofences/pontos conhecidos
```

Ideia de evidência forte:

```text
GPS entra no raio de um ponto
+ dispositivo conecta a uma rede institucional conhecida
=> aumenta a confiança de que o ônibus realmente está naquele ponto
```

A UFRB possui cobertura por redes institucionais em vários pontos relevantes. O dispositivo deve poder trabalhar com mais de uma rede configurada e nunca deve versionar credenciais reais.

Rastreadores veiculares comerciais foram considerados, mas a direção atual favorece ESP32/GPS/Wi-Fi por permitir integração direta com as regras do BUSIVS.

Isso é planejamento futuro; não está implementado em produção.

---

## 12. Dívidas técnicas conhecidas

- `.venv` ainda está versionada no histórico/árvore e deve ser removida do índice em operação Git dedicada;
- muitas camadas `entry_*` representam evolução incremental e precisam de consolidação futura com testes;
- parte da suíte em `tests/` pertence à base histórica/local;
- a suíte mais relevante para produção está em `cloudflare/tests/`;
- falta teste de regressão end-to-end do cron/engajamento;
- mudanças no Durable Object/storage exigem compatibilidade com o estado persistido existente.

---

## 13. Ordem de leitura para retomar

1. `docs/GUIA_CONTINUIDADE_IA.md` — este handoff;
2. `CONTINUIDADE.md` — status curto e trabalho imediato;
3. `docs/DOSSIE_MESTRE_BUSIVS.md` — regras e decisões permanentes;
4. `docs/PLANO_EVOLUCAO_BUSIVS.md` — etapas oficiais;
5. `docs/BLOCOS_OPERACIONAIS.md` — blocos/fechamentos/transições;
6. `docs/FLUXO_TELEGRAM.md` — UX efetiva;
7. `docs/ARQUITETURA.md` — mapa técnico;
8. `cloudflare/README.md` — execução/deploy da produção;
9. código e testes da etapa em execução.

`docs/ROADMAP_BETA.md` é histórico e não deve orientar implementação atual.

---

## 14. Regra de trabalho para outra IA

Antes de alterar o BUSIVS:

1. confirme se a mudança afeta produção Cloudflare ou apenas legado local;
2. confronte a ideia com o Dossiê Mestre;
3. confira `cloudflare/src/dados.py` para horários/rota/blocos reais;
4. preserve estado persistente e compatibilidade do Durable Object;
5. adicione/regresse testes quando tocar regras centrais;
6. não altere regra de negócio apenas para “simplificar” arquitetura;
7. atualize Dossiê + Continuidade quando uma decisão for aprovada;
8. não avance de etapa sem validar a anterior.
