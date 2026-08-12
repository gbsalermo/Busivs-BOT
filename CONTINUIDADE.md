# CONTINUIDADE — BUSIVS BOT

Documento técnico para retomar o projeto rapidamente sem perder decisões, problemas encontrados e o estado real da aplicação.

> **Estado em 11/08/2026:** BUSIVS BOT funcional e hospedado em produção no Cloudflare Workers, integrado ao Telegram por webhook e com estado colaborativo compartilhado em Durable Object.

---

# 1. Direção atual do projeto

O protótipo principal foi concluído e a migração para Cloudflare foi validada em produção.

A partir daqui, o desenvolvimento passa para **melhoria contínua orientada pelo uso real**:

```text
problema / melhoria identificada
      ↓
alpha
      ↓
teste local com bot de teste
      ↓
validação
      ↓
merge para main
      ↓
deploy automático Cloudflare
      ↓
observação em produção
```

Testes automatizados continuam importantes quando protegem uma regra crítica ou reproduzem um bug real, mas deixam de ser uma etapa isolada do roadmap.

**Foco imediato:** pequenas melhorias que aumentem eficiência, confiabilidade e clareza antes de ampliar o escopo do produto.

---

# 2. Branches oficiais

O repositório foi reduzido para três branches com papéis claros:

```text
main
→ produção atual
→ conectada ao Cloudflare
→ qualquer push/merge pode gerar deploy

alpha
→ desenvolvimento e testes locais
→ NÃO deve gerar deploy Cloudflare
→ usa um bot de teste separado
→ mudanças devem ser validadas aqui antes da produção

local
→ versão antiga em polling
→ fallback histórico / referência
```

Regra operacional:

> **Mudanças normais entram primeiro em `alpha`. `main` só recebe o que já foi validado.**

Na Cloudflare, manter:

```text
Production branch: main
Builds for non-production branches: desativado
```

Isso evita testar código novo diretamente no bot oficial.

---

# 3. Princípios que não devem ser quebrados

1. Não tratar estimativa como confirmação.
2. Não inferir sentido apenas pelo nome de um ponto.
3. Biblioteca aparece duas vezes e precisa ser interpretada pelo contexto da rota.
4. Horário oficial é referência; atraso real deve ser tolerado.
5. Confirmações colaborativas precisam ser coerentes com rota e tempo.
6. Manter horários, pontos e rota em estruturas simples sempre que possível.
7. Localização é temporária; não criar histórico permanente sem necessidade real.
8. Viagens do mesmo bloco operacional podem compartilhar contexto.
9. Preferir correções pequenas, legíveis e fáceis de manter.
10. Não adicionar infraestrutura sem problema concreto.
11. Preservar a versão local/polling como fallback.
12. Tokens, secrets e credenciais nunca devem ser versionados.
13. Não usar `alpha` para deploy em nuvem; ela é laboratório local.

> **Princípio central:** o BUSIVS deve continuar simples, eficaz e de custo zero ou próximo de zero.

---

# 4. Arquitetura atual — PRODUÇÃO

```text
Telegram
   ↓ webhook HTTPS
Cloudflare Python Worker
   ↓
entry.py
   ↓
regras do BUSIVS
   ↕
BusState — Durable Object / SQLite
   ↓
Telegram Bot API
```

O Worker recebe cada Update do Telegram, valida o secret do webhook, interpreta mensagens/callbacks, consulta ou altera o estado compartilhado e responde pela Telegram Bot API.

Endpoint de saúde:

```text
GET /health
```

---

# 5. Estrutura principal da versão Cloudflare

```text
cloudflare/
├── pyproject.toml
├── pylock.toml
├── wrangler.jsonc
├── src/
│   ├── entry.py
│   ├── telegram_api.py
│   ├── estado_bus.py
│   ├── regras.py
│   ├── plausibilidade.py
│   └── dados.py
└── tests/
```

Responsabilidades:

```text
entry.py
→ HTTP Worker, webhook, menus, callbacks e integração geral

telegram_api.py
→ chamadas HTTP para Telegram Bot API

estado_bus.py
→ Durable Object BusState e persistência do estado operacional

regras.py
→ horários, rota, localização, blocos e registro de passagem

plausibilidade.py
→ proteção contra deslocamentos impossíveis em tempo muito curto

dados.py
→ horários, pontos e rota usados pelo Worker
```

---

# 6. Persistência

A decisão original de evitar um banco tradicional foi mantida.

```text
Dados permanentes de configuração
→ horários / pontos / rota

Estado operacional compartilhado
→ Durable Object

Histórico permanente de localização
→ NÃO existe
```

O Durable Object existe porque Workers não podem depender de memória compartilhada entre requisições.

```text
BUS_STATE → BusState
storage   → SQLite
```

O estado contém apenas informações necessárias para a operação recente: ponto atual/anterior, horário, resultado da rota e histórico curto.

---

# 7. Secrets e deploy

Secrets de produção:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
```

Eles não ficam no GitHub.

A forma que funcionou de modo confiável foi:

```bash
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
```

Depois de cadastrados no Worker, deploys normais não exigem recadastro.

O `.env` é apenas local e deve continuar ignorado pelo Git.

---

# 8. Problemas de infraestrutura já resolvidos

```text
uv não instalado
→ instalação/configuração do uv

falha Pyodide local
→ ajuste da toolchain e validação pelo ambiente Cloudflare

Worker retornando Hello World
→ entrada/configuração de deploy corrigida

webhook_secret_invalid
→ header/secret corrigidos

error code 1101
→ correções na adaptação Worker

secrets ausentes no deploy
→ cadastro persistente com wrangler secret put

BusState provisionado mas ausente dos exports
→ Durable Object reconciliado na configuração

sequência impossível aceita rapidamente
→ camada de plausibilidade física antes do registro
```

Não remover ou alterar de forma casual a declaração do `BusState` em `exports`, pois o namespace já foi provisionado pela Cloudflare.

---

# 9. Funcionalidades em produção

O Circular Principal possui atualmente:

- menu Telegram por botões;
- horários fixos;
- próximos horários;
- listagem por manhã, almoço, tarde e noite;
- previsão de chegada ao Portão 1;
- identificação de pico;
- rota completa;
- pontos opcionais;
- informar passagem;
- estado colaborativo compartilhado;
- última confirmação;
- cálculo de sentido;
- próximo ponto esperado;
- percurso de retorno;
- provável espera na origem;
- pré-saída da Garagem;
- proteção contra registro fora de circulação;
- proteção contra duplicidade imediata;
- histórico operacional curto;
- recuperação de confirmações incompatíveis quando possível;
- blocos operacionais;
- expiração de estado antigo;
- estimativa experimental de possível atraso;
- proteção contra deslocamentos fisicamente improváveis.

Micro-ônibus ainda não foi implementado.

Autenticação institucional continua adiada até existir necessidade demonstrada.

---

# 10. Rota principal

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

A Biblioteca aparece duas vezes. A análise trabalha com ocorrências/índices, não apenas com ID do ponto.

---

# 11. Blocos operacionais

```text
intervalo entre saídas <= 60 min
→ mantém contexto operacional

intervalo entre saídas > 60 min
→ quebra de bloco
→ contexto antigo pode expirar
```

Também há expiração quando o registro pertence a outro dia.

Uma confirmação real recente não deve ser invalidada automaticamente porque o horário teórico mudou.

---

# 12. Recuperação e plausibilidade das confirmações

Uma confirmação isolada incorreta não deve destruir a sessão. O histórico curto permite reconstruir movimento quando uma sequência posterior coerente aparece.

Porém, essa flexibilidade não pode aceitar deslocamentos impossíveis.

Bug real já corrigido:

```text
Biblioteca
↓ poucos segundos
Pavilhão I
↓ poucos segundos
RU
```

A camada `plausibilidade.py` passou a validar distância lógica + tempo antes de alterar o estado.

```text
pontos próximos
→ tolerância alta

salto de vários trechos rápido demais
→ rejeitado

salto longo após tempo plausível
→ pode ser aceito
```

A proteção é conservadora porque o momento do clique não é GPS.

---

# 13. Observabilidade

Cloudflare Observability/Logs pode ser usado para acompanhar requisições e erros.

Terminal em tempo real:

```bash
npx wrangler tail --name busivs-bot
```

Na fase atual, logs devem ajudar a decidir o que corrigir; não devemos adicionar complexidade antes de observar um problema real.

---

# 14. Estado das etapas

```text
Etapa 1   Base do bot                                  ✅
Etapa 2   Horários fixos do Principal                 ✅
Etapa 3   Pontos / rota / sentido / próximo ponto     ✅
Etapa 4   Informar passagem                           ✅
Etapa 5   Localização / tempo / estados / proteção    ✅
Etapa 5.5 Blocos operacionais                         ✅
Etapa 6   Cloudflare / hospedagem                     ✅ PRODUÇÃO
  6.1 Worker HTTP                                     ✅
  6.2 Webhook Telegram                                ✅
  6.3 Interface Telegram                              ✅
  6.4 Durable Object                                  ✅
  6.5 Ciclo operacional                               ✅
  6.6 Equivalência                                    ↪ absorvida pelo uso real
  6.7 Deploy / campo                                  ✅
```

---

# 15. Próxima frente — Avisos e operação remota

A próxima melhoria de produto será **Avisos**, mas ela deve ser pensada junto com a operação remota do serviço.

## 15.1 Avisos

Precisamos definir:

```text
- quem pode criar/editar/remover aviso;
- onde o aviso fica armazenado;
- validade/expiração automática;
- prioridade/tipo do aviso;
- como o usuário consulta pelo botão 📢 Avisos;
- se haverá aviso destacado em outras respostas;
- como administrar isso sem precisar estar no computador.
```

Pergunta operacional central:

> **Como Gabriel envia um aviso quando estiver longe do computador?**

Possibilidades a avaliar na implementação:

```text
A) comandos administrativos pelo próprio Telegram;
B) painel/admin HTTP protegido;
C) edição de arquivo + deploy — pouco prática para urgências;
D) ferramenta externa apenas se houver necessidade real.
```

Preferência conceitual inicial: **administração pelo próprio Telegram**, com autorização por Telegram ID, porque permite agir pelo celular e evita criar um painel separado apenas para isso.

Ainda precisa ser desenhado e validado antes de implementar.

## 15.2 Mudança operacional de rota por fechamento de portão

Fechamento de Portão 1 ou Portão 2 **não é apenas um aviso**.

Pode alterar:

```text
- sequência real dos pontos;
- sentido observado;
- tempo da volta;
- previsão do Portão 1;
- duração estimada de ida/retorno;
- plausibilidade entre confirmações;
- mensagens de localização.
```

Portanto precisamos modelar um **estado operacional de rota**, por exemplo:

```text
rota_normal
portao_1_fechado
portao_2_fechado
outro_desvio
```

Cada estado deverá conseguir alterar simultaneamente:

```text
rota ativa
avisos exibidos
estimativas de tempo
```

Não resolver fechamento de portão somente com texto de aviso.

## 15.3 Administração pelo celular

Além dos avisos, avaliar um pequeno conjunto de comandos restritos ao administrador:

```text
/admin
/aviso
/rota_operacional
/status
/reiniciar_estado
```

Esses comandos devem ser autenticados por Telegram ID e nunca aparecer para usuários normais.

O objetivo é permitir administrar o serviço remotamente sem depender do notebook.

## 15.4 Reinício / recuperação do serviço

Precisamos documentar e decidir o procedimento oficial para situações diferentes.

Questões abertas:

```text
- quando realmente é necessário "reiniciar" um Worker serverless?
- reiniciar significa novo deploy, rollback ou limpar estado?
- como fazer isso pelo painel Cloudflare?
- quando usar Git/main para gerar novo deploy?
- como fazer rollback rápido para uma versão anterior?
- como limpar somente o Durable Object sem redeployar código?
- qual procedimento usar se o Telegram estiver ativo mas o estado estiver corrompido?
```

A decisão deverá separar três ações diferentes:

```text
REDEPLOY
→ republicar código

ROLLBACK
→ voltar versão do Worker

RESET DE ESTADO
→ limpar BusState sem mexer no código
```

Não tratar as três como se fossem "reiniciar o bot".

---

# 16. Fase atual — melhorias pequenas de produção

Antes de ampliar demais o escopo, priorizar:

```text
1. Avisos e administração remota
2. melhor feedback das ações
3. menos cliques desnecessários
4. tratamento de confirmações conflitantes
5. ajuste de tempos/tolerâncias com uso real
6. logs úteis para diagnóstico
7. redução de chamadas desnecessárias à Telegram Bot API
8. revisão da expiração de estado
9. tratamento de erros sem derrubar webhook
10. observação do consumo Worker/Durable Object
11. manutenção de respostas rápidas
```

Escolher uma melhoria por vez.

---

# 17. Pós-protótipo / futuras funcionalidades

Itens já registrados para depois da consolidação da versão atual:

```text
1. Avisos, comunicados e ocorrências
2. Principal + Micro
3. NFC nos pontos
4. Desvios / fechamento dos portões
5. Modo de férias
6. Refinamento das estimativas com dados reais
7. Proteções adicionais contra abuso ou informação incorreta
8. Autenticação institucional — somente se necessária
9. Avisos e alertas automáticos
10. Métricas e estatísticas — somente se gerarem valor real
```

Observação: **Avisos** e **desvios de portões** deixam de ser apenas ideias futuras e entram agora na frente ativa de desenho do produto.

---

# 18. O que NÃO fazer agora

Evitar:

- frontend web apenas por estética;
- PostgreSQL/MySQL sem necessidade;
- cadastro de usuário preventivo;
- histórico permanente de localização;
- autenticação institucional sem demanda real;
- reescrever o projeto em outro framework;
- transformar estimativas em afirmações absolutas;
- resolver antecipadamente todos os abusos possíveis;
- expandir para Micro antes de estabilizar o Principal.

---

# 19. Procedimento de mudança

```text
1. identificar problema/melhoria
2. atualizar alpha a partir da main se necessário
3. implementar na alpha
4. testar localmente com bot de teste
5. corrigir até validar
6. merge para main
7. Cloudflare publica produção
8. observar logs/comportamento
9. registrar decisões relevantes no CONTINUIDADE
```

---

# 20. Resumo para retomada rápida

```text
PRODUÇÃO
main
Cloudflare Worker Python
Telegram Webhook
Durable Object BusState / SQLite

DESENVOLVIMENTO
alpha
execução/testes locais
bot Telegram separado de teste
sem deploy Cloudflare

FALLBACK
local
versão antiga em polling

FASE ATUAL
avisos + operação remota + pequenas melhorias

QUESTÕES PRIORITÁRIAS
como enviar avisos pelo celular
como alterar rota quando portões fecharem
como ajustar estimativas durante desvios
como fazer redeploy/rollback/reset de estado corretamente

PRIORIDADE
confiabilidade + eficiência + simplicidade
```

> **O BUSIVS está em produção. A próxima fase não é aumentar o projeto indiscriminadamente, e sim torná-lo fácil de operar e confiável no dia a dia.**
