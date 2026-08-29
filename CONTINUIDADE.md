# CONTINUIDADE — BUSIVS BOT

Documento curto para retomar o desenvolvimento rapidamente.

> Atualizado em 28/08/2026 durante a Etapa 1 — Fundação de Analytics.

## Estado atual

Produção:

```text
main -> Cloudflare Workers + Telegram Webhook + Durable Object
```

Branch em desenvolvimento:

```text
feat/analytics-fundacao
```

A `main` permanece com o estado estável anterior. A fundação de Analytics ainda deve ser validada antes de merge/deploy.

## Fonte de verdade

Regras permanentes e arquitetura:

```text
docs/DOSSIE_MESTRE_BUSIVS.md
```

Analytics:

```text
docs/ANALYTICS.md
```

Plano futuro:

```text
docs/PLANO_EVOLUCAO_BUSIVS.md
```

Arquitetura resumida:

```text
docs/ARQUITETURA.md
```

Auditoria da limpeza:

```text
docs/AUDITORIA_ETAPA_0.md
```

---

## Produção efetiva

Configuração externa:

```text
cloudflare/wrangler.jsonc
```

Entrypoint:

```text
cloudflare/src/entry_engajamento_final.py
```

Configuração relevante:

```text
Worker: busivs-bot
Cron: * * * * *
Durable Object: BUS_STATE -> BusState
Storage: sqlite
```

Cadeia principal atual:

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

Não remover módulos `entry_*` apenas pelo nome; existem heranças e imports auxiliares.

---

## Regras centrais preservadas

```text
confirmação confiável > inferência pelo trajeto > horário
```

1. horário é referência, não prova automática de posição;
2. dentro do bloco, relógio sozinho não troca a volta;
3. fim real de bloco pode encerrar o contexto e impedir vazamento para o bloco seguinte;
4. RU confiável encerra volta, mas não inicia a próxima sozinho;
5. nova volta pode ser reconhecida pela sequência real da rota;
6. Biblioteca é ambígua e depende de contexto;
7. salto suspeito vira indicação não confiável em vez de ser bloqueado;
8. indicação suspeita não substitui estado confiável;
9. Principal e Micro permanecem independentes;
10. última volta mantém o percurso de retorno sentido Garagem sem esconder pontos ainda atendidos.

Detalhes completos: `docs/DOSSIE_MESTRE_BUSIVS.md`.

---

## Engajamento colaborativo

Regras atuais:

- candidatos vêm de usuários que consultaram `Onde está o ônibus?`;
- operação precisa estar válida;
- primeiro lote ~5 min normal / ~10 min pico;
- segundo lote ~15 min normal / ~20 min pico;
- máximo de 2 lotes coletivos por volta;
- fallback individual do último autor pode existir;
- convite expira em 3 min;
- nova confirmação confiável reinicia a lacuna de silêncio;
- administrador não entra normalmente no lote coletivo;
- limite efetivo de até 20 usuários por lote.

`entry_engajamento.py` mantém constante-base 10, mas `entry_engajamento_final.py` sobrescreve `_eng.MAX_CONVIDADOS = 20`; portanto o Worker efetivo usa 20.

---

## Etapa 0 — concluída e incorporada à main

Foi realizado:

- Dossiê Mestre;
- arquitetura real Cloudflare documentada;
- plano oficial de evolução;
- auditoria da cadeia efetiva;
- README/Continuidade reorganizados;
- `.gitignore` reforçado;
- roadmap Beta antigo marcado como histórico.

A `.venv` já versionada continua reservada para uma limpeza Git dedicada.

---

## Etapa 1 — Fundação de Analytics

Branch:

```text
feat/analytics-fundacao
```

Implementado:

- `cloudflare/src/analytics.py`;
- armazenamento por dia no Durable Object;
- usuários únicos por hash, sem Telegram ID bruto no novo armazenamento;
- primeira e última interação;
- total de interações;
- total de usuários registrados desde a implantação;
- eventos de localização, horários, marcações, Principal, Micro e engajamento;
- separação das ações do administrador;
- distinção entre tentativa de marcação e confirmação aceita;
- RPC `resumo_analytics(dias)` para futura interface administrativa;
- testes em `cloudflare/tests/test_analytics.py`;
- documentação em `docs/ANALYTICS.md`.

Regra obrigatória implementada:

```text
falha de analytics nunca pode impedir o funcionamento normal do BUSIVS
```

Analytics está integrado somente na camada final e usa chaves próprias do Durable Object. Não houve alteração de `wrangler.jsonc`, binding, cron, horários, rota, blocos ou regras de confiabilidade.

### Antes do merge

Validar:

1. `/start` e menu;
2. `Onde está o ônibus?`;
3. marcação Principal normal;
4. fluxo de ponto suspeito;
5. Micro;
6. convite de engajamento;
7. persistência dos novos dados;
8. ausência de regressão nas regras operacionais.

---

## Próxima etapa após validação/merge

```text
ETAPA 2 — Painel administrativo 📊 Estatísticas
```

Usará `resumo_analytics()` para apresentar hoje, 7 dias, 30 dias, total, interações e eventos sem depender do painel da Cloudflare.

---

## Ao retomar o projeto

Leia nesta ordem:

1. `CONTINUIDADE.md`;
2. `docs/DOSSIE_MESTRE_BUSIVS.md`;
3. `docs/ANALYTICS.md`;
4. `docs/PLANO_EVOLUCAO_BUSIVS.md`;
5. `docs/AUDITORIA_ETAPA_0.md`;
6. `docs/ARQUITETURA.md`;
7. arquivos específicos da etapa em execução.
