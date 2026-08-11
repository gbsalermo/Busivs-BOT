# CONTINUIDADE - BUSIVS BOT

Documento técnico de retomada rápida do projeto.

---

# Regras importantes para contribuir

Antes de mexer no projeto:

1. **Não tratar estimativa como confirmação.**
2. **Não inferir sentido apenas pelo nome do ponto.**
3. **Manter horários, pontos e rotas nos JSONs sempre que possível.**
4. **Considerar atraso real antes de bloquear uma passagem.**
5. **Testar Biblioteca nos dois sentidos ao alterar a lógica de rota.**
6. **Preservar a diferença entre dado confirmado e dado estimado.**
7. **Localização é temporária; não criar histórico permanente sem necessidade real.**
8. **Viagens do mesmo bloco operacional podem compartilhar contexto.**
9. **Preferir soluções pequenas e compreensíveis por outros alunos.**
10. **Não adicionar infraestrutura sem um problema concreto.**
11. **A adaptação Cloudflare não pode quebrar a versão atual em polling.**

> **Princípio principal: o BUSIVS BOT deve ser simples, eficaz e de custo zero ou próximo de zero.**

---

# Estado atual estável

A versão funcional permanece na `main`:

```text
Telegram
   ↓ long polling
Python + python-telegram-bot
   ↓
JSON = horários / pontos / rota
Memória = contexto temporário do ônibus
```

Arquivos principais:

```text
src/bot.py       → interface Telegram / polling
src/horarios.py  → horários e estimativas
src/passagens.py → colaboração, estado e localização atual
src/rota.py      → sentido e próximo ponto

data/horarios_letivo.json
data/pontos.json
data/rotas.json
```

Dependências atuais da versão principal:

```text
python-telegram-bot
python-dotenv
```

---

# Decisão de persistência

Na versão em polling, continuamos **sem SQL**.

```text
JSON    → informação permanente
Memória → informação atual do bloco operacional
```

O histórico temporário vale enquanto pertence ao mesmo bloco operacional.

Regra atual:

```text
intervalo entre saídas <= 60 min
→ mesmo bloco
→ mantém contexto

intervalo entre saídas > 60 min
→ quebra de bloco
→ contexto antigo pode expirar
```

Também limpa estado de dia anterior.

Banco tradicional só deve ser reconsiderado para histórico de longo prazo, métricas, estatísticas, calibração ou controle de abuso persistente.

**Exceção de infraestrutura:** na versão Cloudflare, Durable Object/SQLite pode ser usado apenas para substituir a memória efêmera do processo, porque Workers não garantem que duas requisições sejam executadas na mesma instância. Isso não muda a decisão de não criar histórico permanente de localização.

---

# Rota principal validada

```text
RU / Residências
↓
Fitotecnia
↓
Prédio de Solos / NEAS / Eng. Florestal
↓
Pavilhão de Aulas I
↓
Biblioteca
↓
Pavilhão de Aulas II
↓
Pavilhão de Engenharia (opcional)
↓
Portão 2 / Tabela
↓
Ponto Externo I / Alex
↓
Ponto Externo II / Canãa
↓
Portão 1
↓
Biblioteca
↓
Torre / COTEC (opcional)
↓
RU / Residências
```

Biblioteca aparece duas vezes. Nunca inferir sentido apenas pelo nome do ponto.

---

# Funcionalidades atuais do protótipo

O Principal já possui:

- horários fixos por período;
- previsão de chegada ao Portão 1;
- identificação de horários de pico;
- próxima saída;
- viagem possivelmente em andamento;
- percurso de retorno;
- provável espera na origem da próxima saída;
- pré-saída da Garagem;
- informar passagem por botões;
- histórico colaborativo curto em memória;
- correção natural de confirmação isolada incompatível;
- sentido e próximo ponto;
- proteção contra passagem fora de circulação;
- ciclo de vida por blocos operacionais;
- regra experimental de possível atraso.

Autenticação institucional continua adiada.

Micro ainda não implementado.

---

# Etapas concluídas

```text
Etapa 1   Base do bot                               ✅
Etapa 2   Horários fixos do Principal              ✅
Etapa 3   Pontos / rota / sentido / próximo ponto  ✅
Etapa 4   Informar passagem                        ✅ protótipo
Etapa 5   Localização / tempo / estados / proteção ✅ protótipo
Etapa 5.5 Blocos operacionais                      ✅ validado
```

---

# Etapa 6 - Cloudflare / versão hospedada

## Objetivo

Testar uma versão de produção com **custo R$ 0**, usando Cloudflare Workers e webhook do Telegram.

A branch exclusiva é:

```text
feat/cloudflare-worker
```

A `main` deve continuar funcionando com `application.run_polling()` até toda a adaptação ser validada.

Arquitetura pretendida:

```text
Telegram
   ↓ webhook HTTPS
Cloudflare Python Worker
   ↓
regras do BUSIVS
   ↕
Durable Object SQLite
   ↓
Telegram Bot API
```

Cloudflare Workers Python está em beta. Por isso a migração será incremental e terá critério claro de abandono.

## 6.1 - Worker HTTP mínimo ✅ em andamento

Objetivo: validar o runtime antes de portar o bot.

Criado:

```text
cloudflare/
├── README.md
├── pyproject.toml
├── wrangler.jsonc
└── src/
    └── entry.py
```

Endpoints iniciais:

```text
GET  /health
POST /telegram/webhook
```

Nesta fase `/telegram/webhook` retorna `501` de propósito.

**Não configurar `setWebhook` ainda.** O Telegram não permite `getUpdates` enquanto um webhook estiver ativo; ativá-lo agora interromperia o bot local em polling.

Critério para concluir 6.1:

```text
[ ] instalar ambiente pywrangler
[ ] rodar Worker localmente
[ ] GET /health retornar 200
[ ] fazer primeiro deploy Cloudflare
[ ] GET /health funcionar na URL pública
```

## 6.2 - Webhook Telegram básico

Objetivo: receber Update sem ainda portar todo o bot.

```text
[ ] TELEGRAM_BOT_TOKEN como secret
[ ] TELEGRAM_WEBHOOK_SECRET como secret
[ ] validar X-Telegram-Bot-Api-Secret-Token
[ ] interpretar update_id / message / callback_query
[ ] responder mensagem simples via Bot API
[ ] configurar setWebhook somente no momento do teste
[ ] documentar como remover webhook e voltar ao polling
```

## 6.3 - Adaptador de interface Telegram

Objetivo: separar regras do BUSIVS das APIs específicas de `python-telegram-bot`.

```text
[ ] menu principal
[ ] próximos horários
[ ] listar horários
[ ] onde está o ônibus
[ ] informar passagem
[ ] callbacks dos pontos
```

As regras de horário/rota devem ser reaproveitadas sempre que o runtime permitir; evitar duplicação de regra de negócio.

## 6.4 - Estado colaborativo no Durable Object

Objetivo: substituir somente a memória temporária que não é confiável em ambiente serverless.

Persistir apenas o contexto operacional curto:

```text
ponto atual
ponto anterior
horário
resultado da rota
histórico curto do bloco
identificador necessário para deduplicação
```

Não transformar essa etapa em banco histórico.

Usar **SQLite-backed Durable Object**, que é a modalidade disponível no Workers Free para novos projetos.

## 6.5 - Ciclo de vida e blocos operacionais

Portar e testar:

```text
mesmo bloco mantém contexto
quebra > 60 min expira contexto
dia anterior expira
atraso não é bloqueado de forma rígida
registros incompatíveis podem ser corrigidos por sequência posterior
```

## 6.6 - Testes de equivalência

Comparar Worker vs versão polling:

```text
[ ] horários
[ ] períodos
[ ] pico
[ ] retorno
[ ] Garagem
[ ] rota ida
[ ] rota retorno
[ ] Biblioteca nos dois sentidos
[ ] pontos opcionais
[ ] colaboração
[ ] registro incorreto seguido de registro correto
[ ] bloco operacional
```

A versão Cloudflare não avança para campo se alterar a regra funcional do protótipo sem intenção.

## 6.7 - Deploy e teste de campo

```text
[ ] deploy definitivo
[ ] secrets configurados
[ ] webhook ativo
[ ] confirmar logs
[ ] confirmar consumo dentro do Free Plan
[ ] teste com poucos alunos
[ ] acompanhar erros e latência
[ ] manter procedimento de rollback para polling
```

---

# Critérios de abandono da Cloudflare

Não insistir na adaptação se ocorrer uma destas situações:

- dependências essenciais incompatíveis com Python Workers;
- CPU do Free Plan insuficiente para o fluxo normal;
- Durable Objects tornarem o projeto desnecessariamente complexo;
- comportamento do webhook ficar menos confiável do que polling;
- necessidade de reescrever grande parte das regras já validadas;
- custo deixar de ser próximo de zero.

Nesse caso:

```text
feat/cloudflare-worker → permanece como experimento
main                   → continua funcional
hospedagem alternativa → VM/worker Python tradicional
```

---

# Testes locais atuais

Executar antes de mudanças relevantes:

```bash
python -m unittest discover -s tests -v
```

Os testes atuais cobrem rota, blocos operacionais e resiliência das confirmações colaborativas.

Na branch Cloudflare, testes específicos devem ficar isolados dos testes do polling sempre que possível.

---

# Pré-hospedagem Cloudflare

```text
[x] regras principais do protótipo testadas localmente
[x] branch de hospedagem isolada
[x] plano gratuito confirmado antes da adaptação
[x] estrutura inicial do Worker criada
[ ] Worker executando localmente
[ ] Worker implantado
[ ] webhook validado
[ ] estado temporário portado
[ ] testes de equivalência concluídos
[ ] teste de campo
```

---

# Próximas etapas de produto depois da hospedagem

A numeração anterior foi deslocada porque a adaptação Cloudflare passou a ser a Etapa 6.

```text
Etapa 7  - Avisos, comunicados e ocorrências ⏳
Etapa 8  - Principal + Micro                 ⏳
Etapa 9  - NFC                               ⏳
Etapa 10 - Desvios dos portões               ⏳
Etapa 11 - Modo de férias                     ⏳
Etapa 12 - Autenticação institucional         ⏳ se necessária
Etapa 13 - Avisos e alertas automáticos       ⏳ pós-protótipo
```

Prioridade após hospedar: testar primeiro o Principal com usuários reais antes de ampliar escopo.

---

# Decisão resumida

```text
MAIN
polling + memória
= versão estável / fallback

FEAT/CLOUDFLARE-WORKER
webhook + Worker + Durable Object
= versão experimental de hospedagem gratuita
```

> **O objetivo da Etapa 6 não é melhorar a arquitetura por vaidade. É conseguir colocar o BUSIVS online por R$ 0 sem perder o comportamento que já foi validado.**
