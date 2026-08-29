# Auditoria — Etapa 0 / Limpeza da Casa

Data: 28/08/2026  
Branch: `chore/etapa-0-limpeza-dossie`

## Objetivo

Organizar o projeto sem alterar regras de negócio ou comportamento operacional do BUSIVS.

A estratégia adotada foi conservadora:

- documentar antes de refatorar;
- separar Cloudflare de regras internas;
- identificar legado sem apagá-lo por aparência;
- não mudar estado persistente;
- não trocar entrypoint;
- não alterar webhook, cron, rota, blocos, Principal ou Micro.

## Arquitetura confirmada

### Camada externa

`cloudflare/wrangler.jsonc` define:

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

Importante: existem imports auxiliares fora dessa linha. O mapa serve como referência, não como autorização automática para remover arquivos.

## Achados

### 1. Documentação arquitetural antiga

`docs/ARQUITETURA.md` descrevia uma arquitetura planejada anterior à produção atual, com `bot.py`, JSON e SQLite local.

Ação:

- substituída pela arquitetura efetiva Cloudflare + Durable Object.

### 2. Continuidade acumulava regra demais

`CONTINUIDADE.md` virou um documento extenso de regras e ainda apontava para um entrypoint anterior.

Ação:

- transformado em documento curto de status/próximo passo;
- regras permanentes migradas para o Dossiê Mestre.

### 3. Ausência de Dossiê Mestre

A arquitetura e as decisões estavam espalhadas entre conversa, continuidade e camadas de código.

Ação:

- criado `docs/DOSSIE_MESTRE_BUSIVS.md`.

### 4. Roadmap Beta obsoleto

`docs/ROADMAP_BETA.md` descrevia etapas de um protótipo anterior e podia induzir novas implementações incompatíveis.

Ação:

- mantido como documento histórico com ponte para o plano atual.

### 5. `.venv` versionada

A árvore do repositório contém `.venv` e dependências locais.

Ação aplicada:

- `.gitignore` ampliado para impedir novos arquivos de ambiente virtual, cache, Wrangler, IDE e logs.

Ação NÃO executada nesta branch:

- remoção física em massa da `.venv` já versionada.

Motivo:

- pela API isso exigiria grande quantidade de deleções;
- a remoção é mais segura em uma operação Git dedicada (`git rm -r --cached .venv`) e não afeta a produção quando feita corretamente.

### 6. Limite de engajamento 10 x 20

`entry_engajamento.py` mantém:

```text
MAX_CONVIDADOS = 10
```

Porém o entrypoint final efetivo contém:

```python
_eng.MAX_CONVIDADOS = 20
```

Conclusão:

- produção efetiva está configurada para até 20 candidatos por lote;
- não alterar a constante-base isoladamente durante a limpeza;
- futura consolidação pode remover essa sobreposição, mas somente com teste de regressão.

## Alterações realizadas

```text
.gitignore
README.md
CONTINUIDADE.md
docs/ARQUITETURA.md
docs/ROADMAP_BETA.md
docs/DOSSIE_MESTRE_BUSIVS.md
docs/PLANO_EVOLUCAO_BUSIVS.md
docs/AUDITORIA_ETAPA_0.md
```

## Alterações funcionais realizadas

```text
NENHUMA
```

Não foram alterados nesta Etapa 0:

- `cloudflare/wrangler.jsonc`;
- entrypoint de produção;
- regras de rota;
- regras de volta;
- blocos operacionais;
- lógica de RU/Biblioteca/Garagem;
- antiteleporte;
- Durable Object;
- webhook;
- cron;
- Principal;
- Micro;
- engajamento efetivo.

## Código legado

Nenhuma camada `entry_*` foi removida.

Decisão:

A dívida técnica existe, mas consolidar essas camadas sem cobertura de regressão é mais arriscado do que mantê-las.

Refatoração futura deverá seguir:

```text
mapear dependência
-> cobrir comportamento com teste
-> consolidar em branch
-> validar Cloudflare + Telegram
-> só então remover legado
```

## Documentação oficial após Etapa 0

```text
CONTINUIDADE.md
= status e próxima etapa

docs/DOSSIE_MESTRE_BUSIVS.md
= fonte de verdade das regras e arquitetura

docs/PLANO_EVOLUCAO_BUSIVS.md
= roadmap oficial

docs/ARQUITETURA.md
= visão técnica resumida
```

## Próximo passo

Após validar e promover esta limpeza:

```text
ETAPA 1 — Fundação de Analytics
```

A implementação de analytics deve ser tolerante a falhas e nunca bloquear o fluxo operacional do BUSIVS.
