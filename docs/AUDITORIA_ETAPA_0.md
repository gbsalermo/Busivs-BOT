# Auditoria — Etapa 0 / Limpeza da Casa

Data original: 28/08/2026  
Encerramento verificado: 31/08/2026

> Documento histórico da Etapa 0. Em 31/08/2026 foi confirmado que `main` e `chore/etapa-0-limpeza-dossie` apontavam para o mesmo commit (`b7885138`), portanto a Etapa 0 deve ser considerada **concluída e incorporada à main**.

## Objetivo da Etapa 0

Organizar o projeto sem alterar regras de negócio ou comportamento operacional do BUSIVS.

Estratégia adotada:

- documentar antes de refatorar;
- separar produção Cloudflare da base histórica/local;
- identificar legado sem apagá-lo por aparência;
- não mudar estado persistente;
- não trocar regras de rota/bloco;
- consolidar uma fonte de verdade para decisões.

---

## Arquitetura confirmada

### Camada externa

`cloudflare/wrangler.jsonc` define atualmente:

```text
main: src/entry_engajamento_final.py
cron: * * * * *
BUS_STATE -> BusState
storage: sqlite
```

### Camada interna

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

Existem imports auxiliares fora dessa linha. O mapa serve como referência, não como autorização automática para remover arquivos.

---

## Achados da limpeza

### 1. Documentação arquitetural antiga

A documentação inicial descrevia `bot.py`, JSON/SQLite local e polling como arquitetura principal.

Ação:

- documentação oficial passou a representar Cloudflare Worker + Telegram Webhook + Durable Object;
- `src/` foi classificado como base histórica/local;
- `cloudflare/` passou a ser explicitamente a referência de produção.

### 2. Continuidade acumulava regras e status antigo

Ação:

- `CONTINUIDADE.md` foi transformado em status curto/próximo trabalho;
- regras permanentes foram consolidadas no Dossiê Mestre;
- em 31/08 o arquivo foi novamente sincronizado para registrar a Etapa 0 como concluída.

### 3. Ausência de Dossiê Mestre

A arquitetura e as decisões estavam espalhadas entre conversas, continuidade e código.

Ação:

- criado `docs/DOSSIE_MESTRE_BUSIVS.md` como fonte de verdade de regras e decisões.

### 4. Roadmap Beta obsoleto

`docs/ROADMAP_BETA.md` descrevia etapas de um protótipo anterior.

Ação:

- preservado como histórico;
- não deve orientar implementação atual.

### 5. `.venv` versionada

A árvore contém ambiente virtual previamente versionado.

Ação aplicada:

- `.gitignore` ampliado.

Ação pendente:

```text
remover os arquivos já rastreados em operação Git dedicada
```

Essa limpeza não deve ser misturada com regra funcional.

### 6. Limite de engajamento 10 x 20

`entry_engajamento.py` mantém:

```text
MAX_CONVIDADOS = 10
```

mas o entrypoint final executa:

```python
_eng.MAX_CONVIDADOS = 20
```

Conclusão:

```text
produção efetiva = até 20 candidatos por lote
```

A sobreposição só deve ser consolidada com teste de regressão.

### 7. Engajamento fora do entrypoint

Em 25/08/2026 foi observado que os avisos proativos não estavam chegando.

Causa encontrada:

```text
wrangler main -> entry_consistencia.py
```

mesmo com a lógica de engajamento presente em outra camada.

Correções realizadas:

```text
66ce4f3 — reintegra avisos colaborativos ao entrypoint final
020f09c — wrangler usa entry_engajamento_final.py
2a14042 — aumenta lote efetivo para 20
```

Situação após auditoria de 31/08:

```text
correção presente no código
cron configurado
validação real/controlada pós-correção ainda necessária
```

Foi criado um gate operacional antes da Etapa 1 para essa validação e para regressão do fluxo proativo.

### 8. Fluxo Telegram antigo

`docs/FLUXO_TELEGRAM.md` descrevia autenticação institucional, código por e-mail, NFC e modo de férias como se fizessem parte do produto.

Confronto com produção:

- o fluxo atual é baseado em botões inline;
- não há autenticação institucional obrigatória;
- não há NFC oficial em produção;
- feedback simples já existe;
- seleção administrativa de volta/Garagem existe.

Ação:

- fluxo reescrito com base nas camadas Cloudflare atuais;
- ideias não implementadas foram marcadas como históricas/futuras.

### 9. Bloco experimental das 20:00

`cloudflare/src/dados.py` possui referência/bloco das 20:00 explicitamente experimental, mas a documentação de blocos não o incluía.

Ação:

- documentação sincronizada;
- 20:00 passa a ser registrada como experimental e não garantida.

---

## Alterações funcionais da Etapa 0

```text
NENHUMA
```

A revisão documental não deve alterar:

- rota;
- referência de volta;
- Principal;
- Micro;
- antiteleporte;
- Durable Object;
- webhook;
- cron;
- regras de bloco;
- comportamento do engajamento.

As correções de engajamento de 25/08 são anteriores e foram apenas registradas na documentação.

---

## Documentação oficial após encerramento

```text
docs/GUIA_CONTINUIDADE_IA.md
= handoff completo para outra IA

CONTINUIDADE.md
= estado atual + próximo trabalho

docs/DOSSIE_MESTRE_BUSIVS.md
= regras e decisões permanentes

docs/PLANO_EVOLUCAO_BUSIVS.md
= roadmap oficial

docs/ARQUITETURA.md
= visão técnica

docs/BLOCOS_OPERACIONAIS.md
= blocos/transições

docs/FLUXO_TELEGRAM.md
= UX atual

docs/SETUP_LOCAL.md
= setup atual

cloudflare/README.md
= produção/deploy
```

---

## Próximo passo após Etapa 0

```text
GATE OPERACIONAL
-> validar engajamento proativo pós-correção
-> criar regressão essencial

ETAPA 1
-> Fundação de Analytics
```

Analytics deve continuar sendo observacional e nunca bloquear o funcionamento normal do BUSIVS.
