# CONTINUIDADE — BUSIVS BOT

Documento técnico para retomar o projeto rapidamente sem depender do histórico da conversa.

> **Estado em 12/08/2026:** BUSIVS BOT funcional em produção no Cloudflare Workers, integrado ao Telegram por webhook, com localização colaborativa do Circular Principal, suporte ao Micro-ônibus de reforço, avisos operacionais e estado compartilhado em Durable Object.

---

# 1. Objetivo do projeto

O BUSIVS BOT auxilia estudantes da **UFRB — Campus Cruz das Almas** a acompanhar o transporte interno pelo Telegram.

O sistema combina:

- horários oficiais;
- regras da rota;
- confirmações colaborativas de passagem;
- estimativas de posição/sentido;
- avisos operacionais;
- acompanhamento separado do Circular Principal e do Micro-ônibus de reforço.

O BUSIVS não usa GPS. Uma confirmação real de usuário e uma estimativa baseada no horário são tratadas como coisas diferentes.

> **Princípio central:** manter o serviço simples, útil e gratuito ou próximo de custo zero.

---

# 2. Branches atuais

```text
main
→ produção Cloudflare / Telegram Webhook

alpha
→ desenvolvimento e testes locais por polling no Telegram

local
→ versão original em polling preservada como referência/fallback
```

A `alpha` **não deve ser conectada à Cloudflare**.

Fluxo normal:

```text
alteração funcional
→ testar na alpha
→ validar no Telegram local
→ portar/adaptar para main
→ deploy Cloudflare
```

---

# 3. Arquitetura de produção

```text
Telegram
   ↓ webhook HTTPS
Cloudflare Python Worker
   ↓
cloudflare/src/entry.py
   ↓
regras do BUSIVS
   ↕
BusState — Durable Object / SQLite
   ↓
Telegram Bot API
```

Endpoint público de saúde:

```text
GET /health
```

Worker de produção:

```text
busivs-bot
```

URL usada em produção durante a implantação:

```text
https://busivs-bot.enzogabrielskull.workers.dev
```

---

# 4. Estrutura importante

```text
cloudflare/
├── wrangler.jsonc
├── pyproject.toml
└── src/
    ├── entry.py
    ├── estado_bus.py
    ├── regras.py
    ├── dados.py
    ├── telegram_api.py
    ├── validacao_rota.py
    ├── avisos_blocos.py
    ├── biblioteca_contexto.py
    ├── ciclo_noturno.py
    ├── expiracao_volta.py
    ├── horarios_pico.py
    └── micro.py

local_test/
├── bot_local.py
├── estado_local.py
├── micro.py
└── estado_teste.json   # local / não versionar
```

Responsabilidades principais:

```text
entry.py
→ webhook, menus, callbacks, ajuda, avisos e integração Telegram

estado_bus.py
→ Durable Object, estado do principal, estado do micro e avisos

regras.py
→ regras centrais de localização e passagem

dados.py
→ horários, pontos e rota

validacao_rota.py
→ proteção contra deslocamentos improváveis

avisos_blocos.py
→ expiração dos avisos conforme o bloco operacional

micro.py
→ referências oficiais e situação de horário do micro
```

---

# 5. Persistência

Não existe banco relacional tradicional.

```text
Configuração permanente
→ código / estruturas de horários e rota

Estado operacional compartilhado
→ Durable Object

Histórico permanente de usuários/localização
→ NÃO existe
```

O Durable Object mantém somente o necessário para a operação recente.

Estados independentes:

```text
estado
→ Circular Principal

estado_micro
→ Micro-ônibus de reforço
```

---

# 6. Funcionalidades atuais

Menu do usuário:

```text
🚌 Onde está o ônibus?
📍 Informar ponto atual
⏰ Próximos horários
📋 Listar horários
🚐 Confirmar que micro está rodando
❓ Ajuda
```

Quando o micro está ativo:

```text
🚐 Micro em operação ✅
```

O botão passa a ser apenas informativo e não renova a ativação.

Para o administrador também aparece:

```text
📢 Avisos
```

---

# 7. Circular Principal

Funcionalidades implementadas:

- horários oficiais;
- listagem por período;
- próximas voltas;
- rota completa;
- localização colaborativa;
- sentido estimado;
- próximo ponto esperado;
- espera na origem;
- pré-saída da Garagem;
- tratamento especial dos blocos noturnos;
- expiração da confirmação antiga após nova saída oficial + tolerância;
- contexto de viagens próximas em horário de pico;
- proteção contra duplicidade;
- proteção contra saltos fisicamente improváveis;
- interpretação contextual da Biblioteca, que aparece duas vezes na rota;
- avisos operacionais com impacto contextual nas respostas.

Horário oficial é referência e não substitui uma confirmação real recente.

---

# 8. Rota principal

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

A Biblioteca aparece duas vezes. Não inferir sentido apenas pelo ID/nome do ponto.

---

# 9. Micro-ônibus de reforço

O Micro é um **reforço**, não substitui o Circular Principal.

Ele pode ou não operar em determinado dia. Por isso o estado precisa ser confirmado colaborativamente.

Ativação:

```text
🚐 Confirmar que micro está rodando
→ "Você viu o micro?"
→ ✅ Sim, está rodando
```

Qualquer usuário pode confirmar que viu o micro operando.

Depois da ativação:

- botão vira `🚐 Micro em operação ✅`;
- Principal e Micro passam a ter estados separados;
- `Informar ponto atual` pergunta qual veículo foi visto;
- `Onde está?` mostra os dois veículos separados;
- `Próximos horários` mostra 2 referências do principal + micro;
- o horário da ativação é registrado e exibido ao usuário.

O administrador pode desativar o micro pelo painel de avisos.

## Horários oficiais cadastrados do micro

Manhã:

```text
07:25 — Garagem → fim 07:40
07:40 — RU/Residências → fim 07:55
07:55 — RU/Residências → fim 08:20
```

Meio-dia:

```text
11:30 — Garagem → fim 11:55
11:55 — RU/Residências → fim 12:20
12:20 — RU/Residências → fim 12:45
```

Não existem mais horários artificiais de teste no código de produção.

## Expiração do micro

Se for ativado durante a faixa oficial entre 07:25 e 13:00:

```text
expira automaticamente às 13:00
```

A última volta termina às 12:45 e existe uma carência até 13:00.

Se for ativado fora da escala oficial, por exemplo em operação extraordinária:

```text
não recebe expiração automática às 13:00
→ permanece ativo até desativação administrativa
```

---

# 10. Avisos operacionais

Avisos pré-definidos atuais:

```text
🚪 Portão 1 fechado
🚪 Portão 2 fechado
⚠️ Circular operando com atraso
🛠️ Circular temporariamente fora de operação
🛠️ Circular quebrou em meio ao trajeto
🌧️ Tempo chuvoso, circular pode demorar mais do que o esperado
🧍‍♂️🧍‍♀️ Superlotação do circular
🚐 Micro está rodando!
🚌 Rota alterada temporariamente
📅 Horários especiais hoje
```

Também existe aviso personalizado.

O aviso:

```text
🚐 Micro está rodando!
```

é **somente informativo**. Ele não ativa nem renova o estado operacional do micro.

Avisos ativos aparecem automaticamente para usuários comuns.

Somente o administrador vê o botão `📢 Avisos` e pode:

- ativar aviso pré-definido;
- criar aviso personalizado;
- remover aviso;
- limpar avisos;
- desativar o micro quando ativo.

Limite atual:

```text
3 avisos ativos
```

Os avisos expiram automaticamente conforme o bloco operacional, mas podem ser publicados novamente caso a situação continue.

---

# 11. Administração

A identificação administrativa é feita por:

```text
ADMIN_TELEGRAM_ID
```

O valor deve existir no ambiente do Worker e não deve ser escrito diretamente no código.

O código compara o `from.id` enviado pelo Telegram com `ADMIN_TELEGRAM_ID`.

Quando reconhecido como administrador, o menu ganha:

```text
📢 Avisos
```

Contato mostrado na Ajuda:

```text
75 99978-0174
```

---

# 12. Secrets de produção

Variáveis/secrets necessários:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
ADMIN_TELEGRAM_ID
```

O `wrangler.jsonc` utiliza:

```json
"keep_vars": true
```

para evitar perder variáveis existentes em deploys normais.

Nunca versionar valores reais no GitHub.

## Configurar ADMIN_TELEGRAM_ID pelo Git Bash

Entre na pasta `cloudflare`:

```bash
cd /d/Projetos/Python/BUSIVIS/Busivs-BOT/cloudflare
```

Opcional: conferir conta e secrets já cadastrados:

```bash
npx wrangler whoami
npx wrangler secret list --name busivs-bot
```

Ler o Telegram ID sem exibir na tela:

```bash
read -s ADMIN_TELEGRAM_ID
```

Cole o ID numérico e pressione Enter.

Enviar para a Cloudflare:

```bash
printf '%s' "$ADMIN_TELEGRAM_ID" | npx wrangler secret put ADMIN_TELEGRAM_ID --name busivs-bot
```

Depois que o Wrangler terminar, em **outro comando**:

```bash
unset ADMIN_TELEGRAM_ID
```

Confirmar:

```bash
npx wrangler secret list --name busivs-bot
```

Esperado:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
ADMIN_TELEGRAM_ID
```

### Erro já ocorrido

Não executar:

```bash
... --name busivs-bot unset ADMIN_TELEGRAM_ID
```

Isso faz o Wrangler interpretar `unset` como argumento e gera:

```text
Unknown arguments: unset, ADMIN_TELEGRAM_ID
```

`unset ADMIN_TELEGRAM_ID` deve ser sempre um comando separado.

---

# 13. Rodar localmente pela alpha

A `alpha` usa Telegram por **polling**, sem Cloudflare.

Na raiz do repositório:

```bash
git switch alpha
git pull origin alpha
```

Configurar `.env` local, não versionado:

```env
TELEGRAM_BOT_TOKEN=token_do_bot
ADMIN_TELEGRAM_ID=seu_id_numerico
```

Executar:

```bash
python local_test/bot_local.py
```

Saída esperada:

```text
BUSIVS ALPHA LOCAL iniciado por polling.
```

Parar:

```text
Ctrl+C
```

Estado local:

```text
local_test/estado_teste.json
```

Ele pode manter micro/avisos ativos entre reinicializações. Para um teste realmente limpo, verificar/remover o arquivo ou limpar o estado conscientemente.

Arquivos locais que não devem entrar em commits:

```text
.env
__pycache__/
*.pyc
cloudflare/.wrangler/
local_test/estado_teste.json
```

---

# 14. Deploy de produção

`main` está conectada à Cloudflare por Git.

Fluxo normal:

```text
commit/push na main
→ Cloudflare detecta
→ build/deploy
→ Worker atualizado
```

Um commit vazio pode ser usado para disparar novo deploy quando necessário:

```bash
git switch main
git pull
git commit --allow-empty -m "ci: redeploy cloudflare"
git push origin main
```

Não usar isso como primeira solução para bugs; serve apenas para forçar um novo deploy quando o código/configuração já está corretos.

---

# 15. Problemas importantes já resolvidos

## Durable Object provisionado e ausente dos exports

Erro:

```text
provisioned_class_missing_from_config
```

A classe `BusState` já possuía namespace provisionado. A configuração atual mantém o Durable Object corretamente declarado com armazenamento SQLite.

Não remover/renomear essa declaração casualmente.

## Secrets perdidos em deploy

Os secrets foram cadastrados diretamente com Wrangler. `keep_vars` permanece ativo.

## PyWrangler/Pyodide no Windows

O ambiente local de Worker apresentou falhas de Pyodide. Por isso o teste funcional da `alpha` passou a usar polling direto do Telegram, que é mais simples e confiável para o desenvolvimento atual.

## Saltos impossíveis entre pontos

Existe validação de plausibilidade temporal para impedir sequências fisicamente absurdas sem transformar o sistema em GPS.

## Biblioteca ambígua

A primeira confirmação na Biblioteca usa contexto temporal da volta quando não há histórico suficiente; com histórico, a sequência da rota tem prioridade.

---

# 16. Regras que não devem ser quebradas

1. Estimativa nunca deve ser apresentada como confirmação.
2. Horários oficiais são referência, não prova da posição real.
3. Confirmação real recente válida pode superar ambiguidade de horário.
4. Biblioteca precisa de contexto porque aparece duas vezes.
5. O estado do Principal e do Micro deve permanecer separado.
6. Aviso `Micro está rodando` não deve ativar o modo micro.
7. Usuário comum pode confirmar o micro, mas somente admin pode desativá-lo manualmente.
8. Não criar histórico permanente de usuários/localização sem necessidade concreta.
9. Não versionar tokens, IDs administrativos ou secrets.
10. Preferir mudanças pequenas e testáveis na `alpha` antes da produção.

---

# 17. Pós-protótipo / melhorias futuras

O núcleo funcional está fechado. Priorizar observação do uso real e melhorias justificadas.

Já documentado para pós-protótipo:

- supressão de spam de confirmações repetidas;
- rate limit temporário por usuário/ponto;
- detecção de rajadas anormais;
- proteção contra trotes/invasões;
- consolidação de muitas confirmações idênticas;
- tratamento melhor de confirmações conflitantes;
- bloqueios temporários de fontes abusivas;
- NFC nos pontos;
- verificação por e-mail institucional, se passar a ser necessária;
- modo férias/horários especiais mais estruturado;
- refinamento de estimativas com dados reais de uso.

Não adicionar infraestrutura preventiva sem problema concreto.

---

# 18. Fase atual

A lógica principal foi validada na `alpha` e portada para `main`.

Estado atual:

```text
Circular Principal                  ✅
Micro-ônibus de reforço             ✅
Localização colaborativa            ✅
Avisos operacionais                 ✅
Painel administrativo               ✅
Ajuda e contato                     ✅
Cloudflare Worker                   ✅ produção
Telegram Webhook                    ✅ produção
Durable Object                      ✅ produção
Execução local pela alpha           ✅
```

Próximo foco imediato:

```text
1. revisar textos do bot
2. preparar card de lançamento
3. preparar texto oficial de divulgação
4. observar uso real
5. corrigir somente problemas que aparecerem
```

---

# 19. Resumo de retomada rápida

```text
REPOSITÓRIO
https://github.com/gbsalermo/Busivs-BOT

PRODUÇÃO
branch: main
Cloudflare Worker Python
Telegram Webhook
Durable Object BusState
Circular Principal + Micro + Avisos

TESTE LOCAL
branch: alpha
python local_test/bot_local.py
Telegram polling
estado local em local_test/estado_teste.json

FALLBACK HISTÓRICO
branch: local
versão original em polling

ADMIN
ADMIN_TELEGRAM_ID no ambiente Cloudflare
📢 Avisos só aparece para o administrador

FASE ATUAL
núcleo funcional fechado
foco em textos, lançamento e observação do uso real
```

> **O BUSIVS já é um serviço funcional. A prioridade agora é comunicar bem, observar o uso real e evoluir apenas onde houver necessidade concreta.**
