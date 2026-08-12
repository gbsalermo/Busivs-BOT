# CONTINUIDADE — BUSIVS BOT

Documento técnico para retomar o projeto rapidamente sem perder decisões, problemas encontrados e o estado real da aplicação.

> **Estado em 11/08/2026:** BUSIVS BOT funcional e hospedado em produção no Cloudflare Workers, integrado ao Telegram por webhook e com estado colaborativo compartilhado em Durable Object.

---

# 1. Direção atual do projeto

O protótipo principal foi concluído e a migração para Cloudflare foi validada em produção.

A partir daqui, não existe mais uma etapa formal de bateria de testes antes de cada avanço. O desenvolvimento passa para **melhoria contínua orientada pelo uso real**:

```text
serviço em produção
      ↓
uso real / observação dos logs
      ↓
problema ou oportunidade identificada
      ↓
correção pequena e objetiva
      ↓
deploy
      ↓
validação em uso
```

Testes automatizados continuam úteis e devem ser adicionados principalmente quando protegem uma regra importante ou reproduzem um bug real. Eles deixam de ser uma etapa separada do roadmap.

**Foco imediato:** pequenas melhorias que aumentem eficiência, confiabilidade e clareza sem aumentar desnecessariamente a infraestrutura.

---

# 2. Princípios que não devem ser quebrados

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
11. Preservar a versão original em polling como referência/fallback.
12. Tokens, secrets e credenciais nunca devem ser versionados.

> **Princípio central:** o BUSIVS deve continuar simples, eficaz e de custo zero ou próximo de zero.

---

# 3. Arquitetura atual — PRODUÇÃO

A arquitetura ativa deixou de ser polling local e passou a ser:

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

O endpoint público de saúde é:

```text
GET /health
```

A versão atual identifica o runtime como `cloudflare-worker`.

---

# 4. Organização das versões

Durante a migração foi criada a branch `feat/cloudflare-worker`. Posteriormente a versão Cloudflare foi promovida para `main`.

Para preservar o projeto original foi criada:

```text
mainOriginal
```

Estado conceitual:

```text
main
→ versão atual Cloudflare / produção

mainOriginal
→ versão original em polling preservada como fallback/referência
```

Também existem cópias locais separadas da versão Cloudflare e da versão original.

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
→ carregamento/representação dos horários, pontos e rota usados pelo Worker
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

O Durable Object é necessário porque Workers são serverless e requisições diferentes não podem depender da memória de uma mesma instância Python.

A classe usada é:

```text
BusState
```

Binding:

```text
BUS_STATE → BusState
```

O estado salvo contém apenas informações necessárias para a operação recente, como ponto atual/anterior, horário, resultado da rota e histórico curto.

---

# 7. Problema do Durable Object durante o deploy

Durante a configuração de produção apareceu o erro:

```text
Durable Object exports reconciliation failed
class 'BusState' has a provisioned Durable Object namespace
but is not declared in exports
```

Causa: o namespace já havia sido provisionado pela Cloudflare, mas uma configuração/deploy posterior não declarava `BusState` corretamente nos exports.

A configuração foi corrigida mantendo `BusState` declarado como Durable Object com armazenamento SQLite.

**Não remover essa declaração de forma casual.** Uma vez provisionado, a Cloudflare exige reconciliação explícita caso a classe seja removida, renomeada ou transferida.

---

# 8. Secrets e variáveis de ambiente

Secrets de produção necessários:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
```

Eles não devem estar no GitHub nem em `.env` versionado.

Durante a implantação via integração do repositório ocorreu um problema importante: o deploy reclamava que os secrets obrigatórios não estavam definidos, e a interface de adicionar variável chegou a ser bloqueada pelo erro de reconciliação do Durable Object.

A solução funcional foi cadastrar os secrets diretamente pelo Wrangler:

```bash
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
```

Após cadastrados corretamente no Worker, novos deploys normais não exigem recadastrar os tokens.

O `.env` pode ser usado apenas no ambiente local e nunca deve ser enviado ao repositório.

---

# 9. PyWrangler / Workers Python

Durante a configuração local apareceram problemas com versões antigas do `workers-py`/PyWrangler e com a criação do ambiente Pyodide pelo `uv`.

Exemplos encontrados:

```text
uv: command not found
```

Depois da instalação do `uv`, ocorreu erro ao consultar:

```text
cpython-3.13.2-emscripten-wasm32-musl
```

O ambiente Cloudflare posteriormente conseguiu executar corretamente o fluxo:

```text
uv run pywrangler deploy
→ cria .venv
→ cria .venv-workers
→ baixa Pyodide
→ instala python_modules
→ passa o deploy para npx wrangler
```

O deploy validado utilizou `wrangler 4.121.0` e concluiu o upload do Worker com o binding `BUS_STATE`.

Não alterar versões de runtime/dependências sem necessidade concreta, porque essa camada foi uma das partes mais sensíveis da migração.

---

# 10. Webhook Telegram

Endpoint:

```text
POST /telegram/webhook
```

O Worker valida:

```text
X-Telegram-Bot-Api-Secret-Token
```

contra `TELEGRAM_WEBHOOK_SECRET`.

Durante os testes manuais ocorreu:

```json
{"ok": false, "error": "webhook_secret_invalid"}
```

A validação funcionou como esperado: o header estava incorreto/ausente.

Depois, um POST manual com secret válido retornou:

```json
{"ok": true, "handled": false, "reason": "update_type_not_supported_yet", "stage": "6.2"}
```

Isso confirmou antes da integração completa que URL pública, endpoint, JSON e autenticação estavam funcionando.

Posteriormente o webhook completo foi conectado aos comandos e callbacks do bot.

---

# 11. Funcionalidades em produção

O Circular Principal possui atualmente:

- menu Telegram por botões;
- horários fixos;
- próximos horários;
- listagem por manhã, almoço, tarde e noite;
- previsão aproximada de chegada ao Portão 1;
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
- recuperação de confirmações incompatíveis quando a sequência posterior permite;
- ciclo de vida por blocos operacionais;
- expiração de estado de dia anterior;
- estimativa experimental de possível atraso;
- proteção de plausibilidade física entre confirmações.

Micro-ônibus ainda não foi implementado.

Autenticação institucional continua adiada até existir uma necessidade demonstrada.

---

# 12. Rota principal validada

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

A Biblioteca aparece duas vezes. A função de análise trabalha com ocorrências/índices da rota em vez de assumir um sentido pelo ID do ponto.

---

# 13. Blocos operacionais

O estado não é limpo simplesmente ao terminar uma saída prevista, porque atrasos podem fazer uma viagem atravessar o horário teórico.

Regra geral:

```text
intervalo entre saídas <= 60 min
→ mantém contexto operacional

intervalo entre saídas > 60 min
→ quebra de bloco
→ contexto antigo pode expirar
```

Também há expiração quando o registro pertence a outro dia.

A lógica evita que o horário oficial invalide automaticamente uma confirmação real recente.

---

# 14. Recuperação de registros colaborativos

Uma decisão importante foi permitir recuperação natural de uma confirmação isolada incorreta.

Exemplo conceitual:

```text
A → registro errado → B
```

Se `B` for coerente com uma confirmação anterior do histórico, o sistema pode reconstruir o movimento sem deixar um clique errado destruir toda a sessão.

Essa flexibilidade gerou posteriormente um novo problema: o algoritmo podia aceitar sequências fisicamente impossíveis porque encontrava alguma combinação válida na rota.

---

# 15. Bug encontrado em produção — saltos rápidos impossíveis

Cenário observado:

```text
Biblioteca
↓ poucos segundos
Pavilhão I
↓ poucos segundos
RU
```

Os registros eram aceitos porque a análise de rota encontrava ocorrências posteriores compatíveis e a recuperação histórica podia ignorar uma confirmação incompatível recente.

O problema não era apenas a ordem da rota: faltava considerar o **tempo necessário para o deslocamento**.

Solução aplicada: criação de `plausibilidade.py` e validação antes de alterar o estado.

Princípio atual:

```text
pontos próximos / poucos trechos
→ tolerância alta

salto por vários trechos em tempo extremamente curto
→ rejeitado

salto longo após tempo plausível
→ pode ser aceito
```

A proteção foi propositalmente conservadora para não transformar horário de clique em GPS. O estudante pode informar a passagem alguns segundos depois do ônibus passar.

Quando bloqueado, o estado anterior é preservado e o usuário recebe mensagem explicando que a confirmação parece incompatível com a última passagem.

Testes específicos foram adicionados para esse bug.

---

# 16. Observabilidade

Os logs/Observability do Cloudflare Worker podem ser habilitados no painel. A ativação pode solicitar um novo deploy para aplicar a configuração.

Depois disso, requisições do webhook e execuções do Worker podem ser acompanhadas pelo painel da Cloudflare.

Para acompanhamento ao vivo pelo terminal também pode ser usado:

```bash
npx wrangler tail --name busivs-bot
```

Logs agora são parte importante da fase de melhoria contínua: devem ser usados para investigar comportamento real antes de adicionar complexidade.

---

# 17. Problemas já encontrados e resolvidos

```text
uv não instalado
→ instalação/configuração do uv

falha Pyodide local
→ atualização/ajuste da toolchain e validação pelo ambiente Cloudflare

Worker inicialmente retornando apenas Hello World
→ entrypoint/configuração corrigidos

webhook_secret_invalid
→ header/secret corrigidos e validação confirmada

error code 1101
→ investigação e correções da adaptação Worker

secrets ausentes no deploy
→ cadastro persistente com wrangler secret put

BusState provisionado mas ausente dos exports
→ Durable Object reconciliado na configuração

sequência de pontos impossível aceita rapidamente
→ camada de plausibilidade física antes do registro
```

Esses problemas são importantes porque representam pontos frágeis que podem reaparecer após mudanças de infraestrutura.

---

# 18. Estado das etapas

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

A antiga etapa formal de testes de equivalência não será mantida como bloqueio do roadmap. A equivalência essencial foi validada durante a migração e, daqui em diante, erros serão tratados conforme aparecerem em produção.

---

# 19. Fase atual — melhorias pequenas de produção

Antes de ampliar o escopo do BUSIVS, priorizar melhorias incrementais no serviço existente.

Boas candidatas:

```text
1. melhorar mensagens e feedback de ações
2. reduzir cliques desnecessários
3. melhorar tratamento de confirmações conflitantes
4. ajustar tempos/tolerâncias com observações reais
5. melhorar logs úteis para diagnóstico
6. evitar chamadas desnecessárias à Telegram Bot API
7. revisar expiração do estado conforme situações reais aparecerem
8. melhorar tratamento de erros sem derrubar o webhook
9. observar consumo de Worker/Durable Object
10. manter respostas rápidas no Telegram
```

Não implementar todas antecipadamente. Escolher uma melhoria por vez com base no impacto observado.

---

# 20. Pós-protótipo / futuras funcionalidades

Depois de consolidar a versão atual:

```text
Avisos, comunicados e ocorrências
Principal + Micro
NFC nos pontos
Desvios dos portões
Modo de férias
Refinamento de estimativas com dados reais
Proteções adicionais contra abuso/informação incorreta
Autenticação institucional — somente se necessária
Avisos e alertas automáticos
Métricas/estatísticas — somente se gerarem valor real
```

Prioridade continua sendo fazer o **Principal atual funcionar muito bem** antes de aumentar o escopo.

---

# 21. O que NÃO fazer agora

Evitar neste momento:

- criar frontend web apenas por estética;
- adicionar PostgreSQL/MySQL para substituir o estado simples;
- criar cadastro de usuário sem necessidade;
- armazenar histórico permanente de localização;
- adicionar autenticação institucional preventivamente;
- reescrever o projeto em outro framework;
- transformar estimativas em afirmações absolutas;
- tentar resolver antecipadamente todos os possíveis abusos;
- expandir para Micro antes de estabilizar o Principal.

---

# 22. Procedimento de mudança daqui para frente

Para cada problema encontrado:

```text
1. reproduzir o comportamento
2. identificar qual regra realmente falhou
3. corrigir no menor ponto possível
4. adicionar teste se o bug representar uma regra importante
5. fazer deploy
6. validar no Telegram
7. observar logs/comportamento
8. registrar no CONTINUIDADE se alterar decisão relevante
```

O objetivo não é perseguir arquitetura perfeita. É manter um serviço simples que resolva bem o problema dos estudantes.

---

# 23. Resumo para retomada rápida

```text
PRODUÇÃO
main
Cloudflare Worker Python
Telegram Webhook
Durable Object BusState / SQLite
horários + rota + colaboração
secrets persistidos na Cloudflare
logs disponíveis para observação

FALLBACK
mainOriginal
versão Python em polling

FASE ATUAL
melhorias pequenas e correções orientadas pelo uso real

PRIORIDADE
confiabilidade + eficiência + simplicidade

PRÓXIMO PASSO
observar o serviço em produção e atacar uma melhoria pequena por vez
```

> **O BUSIVS deixou de ser apenas um protótipo local. A versão principal está online; agora o trabalho é fazê-la funcionar cada vez melhor antes de aumentar seu escopo.**

---

# 24. Atualização operacional — 12/08/2026

Esta seção registra o procedimento atual usado depois da implantação do modo Micro e do painel administrativo. Quando houver conflito com instruções antigas deste documento, considerar esta seção como a referência mais recente.

## 24.1 Configurar o administrador no Worker pela linha de comando

A produção usa a variável/secret:

```text
ADMIN_TELEGRAM_ID
```

Ela deve conter **o ID numérico da conta Telegram do administrador**, e não telefone, username ou token do bot.

O código não deve receber esse ID diretamente no repositório. A configuração deve ficar no ambiente do Worker.

No **Git Bash**, entrar na pasta `cloudflare` do projeto e confirmar que o Wrangler está operando sobre o Worker correto:

```bash
cd /d/Projetos/Python/BUSIVIS/Busivs-BOT/cloudflare
npx wrangler whoami
npx wrangler secret list --name busivs-bot
```

Para cadastrar ou atualizar `ADMIN_TELEGRAM_ID` sem deixar o valor visível no histórico do terminal:

```bash
read -s ADMIN_TELEGRAM_ID
```

Colar o ID numérico do Telegram e pressionar Enter. Em seguida executar **em outro comando**:

```bash
printf '%s' "$ADMIN_TELEGRAM_ID" | npx wrangler secret put ADMIN_TELEGRAM_ID --name busivs-bot
```

O resultado esperado é equivalente a:

```text
Success! Uploaded secret ADMIN_TELEGRAM_ID
```

Somente depois executar:

```bash
unset ADMIN_TELEGRAM_ID
```

**IMPORTANTE:** não colocar `unset ADMIN_TELEGRAM_ID` na mesma linha do `wrangler secret put`. Caso isso aconteça, o Wrangler interpreta `unset` como argumento e retorna erro semelhante a:

```text
Unknown arguments: unset, ADMIN_TELEGRAM_ID
```

Confirmar finalmente que o secret existe no Worker:

```bash
npx wrangler secret list --name busivs-bot
```

A lista de produção deve conter pelo menos:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
ADMIN_TELEGRAM_ID
```

O arquivo `cloudflare/wrangler.jsonc` usa:

```json
"keep_vars": true
```

Portanto os secrets/variáveis existentes devem ser preservados durante deploys normais.

Depois da configuração, abrir o bot no Telegram e executar:

```text
/start
```

Para a conta cujo Telegram ID corresponde a `ADMIN_TELEGRAM_ID`, o menu deve incluir:

```text
📢 Avisos
```

Usuários comuns não devem ver esse botão.

Quando o micro estiver ativo, o painel administrativo também permite:

```text
🚐 Desativar micro
```

## 24.2 Rodar a versão local pela branch alpha

A branch destinada a desenvolvimento/testes locais é:

```text
alpha
```

Ela usa polling do Telegram e **não deve ser conectada ao deploy de produção da Cloudflare**.

Fluxo recomendado para iniciar um teste local:

```bash
cd /d/Projetos/Python/BUSIVIS/Busivs-BOT
git switch alpha
git pull origin alpha
python local_test/bot_local.py
```

O bot local lê o arquivo `.env` na raiz do projeto. Ele deve conter localmente:

```env
TELEGRAM_BOT_TOKEN=token_do_bot
ADMIN_TELEGRAM_ID=id_numerico_do_administrador
```

O `.env` **não deve ser commitado**.

A execução correta mostra no terminal:

```text
BUSIVS ALPHA LOCAL iniciado por polling.
```

Enquanto o polling local estiver rodando, utilizar o Telegram normalmente para validar menus, callbacks e regras.

Para encerrar:

```text
Ctrl + C
```

O estado de teste local fica em:

```text
local_test/estado_teste.json
```

Esse arquivo pode preservar entre reinicializações informações como avisos, estado do principal e estado do micro. Se um teste começar com informação antiga, verificar esse arquivo/estado antes de concluir que existe bug no código.

Arquivos temporários locais como `__pycache__`, `.wrangler` e estado de teste não devem ser tratados como alterações funcionais do projeto.

## 24.3 Diferença prática entre main e alpha

```text
main
→ produção
→ Cloudflare Worker
→ webhook Telegram
→ Durable Object compartilhado
→ mudanças podem disparar deploy

alpha
→ desenvolvimento/teste local
→ python local_test/bot_local.py
→ polling Telegram
→ estado local em JSON
→ não deve afetar produção
```

Antes de alterar uma regra em produção, a preferência continua sendo validar primeiro na `alpha` quando a mudança puder ser reproduzida localmente.
