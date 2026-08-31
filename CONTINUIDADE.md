# CONTINUIDADE — BUSIVS BOT

Documento curto para retomar o desenvolvimento rapidamente.

> Atualizado em 31/08/2026 após revisão completa da documentação e confronto com a produção Cloudflare.

## Estado atual

Produção:

```text
main
-> Cloudflare Workers + Telegram Webhook + Durable Object
```

Commit-base auditado antes desta revisão:

```text
b7885138 — docs: fecha status da etapa zero na continuidade
```

A branch histórica:

```text
chore/etapa-0-limpeza-dossie
```

está no mesmo commit que a `main`. Portanto:

```text
ETAPA 0 = CONCLUÍDA E INCORPORADA À MAIN
```

Ela não deve mais ser tratada como etapa aguardando merge.

---

## Leia primeiro

Para uma IA assumir o projeto:

```text
docs/GUIA_CONTINUIDADE_IA.md
```

Fonte de verdade de regras permanentes:

```text
docs/DOSSIE_MESTRE_BUSIVS.md
```

Plano oficial:

```text
docs/PLANO_EVOLUCAO_BUSIVS.md
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

A pasta raiz `src/` representa a base histórica/local por polling e **não é o runtime de produção**.

---

## Regras centrais preservadas

```text
confirmação confiável > inferência pelo trajeto > horário
```

1. horário é referência, não prova automática de posição;
2. dentro do bloco, relógio sozinho não troca a volta;
3. fim real de bloco pode encerrar o contexto e impedir vazamento para o bloco seguinte;
4. RU confiável encerra volta, mas não inicia a próxima sozinho;
5. nova volta pode ser reconhecida pela sequência real da rota quando houver saída oficial compatível;
6. Biblioteca é ambígua e depende de contexto;
7. salto suspeito vira indicação não confiável em vez de ser aceito como estado definitivo;
8. indicação suspeita não substitui estado confiável;
9. Principal e Micro permanecem independentes;
10. última volta mantém o **percurso de retorno sentido Garagem** sem esconder pontos ainda atendidos;
11. depois do encerramento do bloco, uma consulta deve apontar Garagem/próxima saída em vez de manter estado velho indefinidamente.

---

## Horários/blocos — atenção

A fonte oficial é:

```text
cloudflare/src/dados.py
```

O bloco experimental das **20:00** existe no código e deve aparecer na documentação:

```text
20:00 — Garagem — experimental — pode não ocorrer
```

Os blocos noturnos configurados são independentes:

```text
20:00 [experimental]
20:40
21:40
22:30
```

---

## Engajamento colaborativo

Regras atuais:

- candidatos vêm de usuários comuns que consultaram `Onde está o ônibus?`;
- operação do Principal precisa estar válida;
- primeiro lote ~5 min normal / ~10 min pico;
- segundo lote ~15 min normal / ~20 min pico;
- fallback individual do último autor pode existir;
- convite expira em 3 min;
- máximo de 2 lotes coletivos por volta;
- até 20 usuários por lote em produção;
- nova confirmação confiável reinicia a lacuna de silêncio.

### Incidente de 25/08/2026

Foi relatado que os pedidos proativos não estavam chegando. A causa arquitetural encontrada foi que o Worker ainda apontava para `entry_consistencia.py`, deixando a camada final de engajamento fora do entrypoint efetivo.

Correções já presentes na `main`:

```text
66ce4f3 — reintegra avisos colaborativos ao entrypoint final
020f09c — wrangler passa a usar entry_engajamento_final.py
2a14042 — lote efetivo passa a até 20 usuários
```

Status correto para continuidade:

```text
código corrigido
+ cron ativo
+ validação de uso real pós-correção ainda é necessária
```

A suíte atual também não possui teste end-to-end equivalente do cron + seleção + envio do convite. Isso deve ser tratado como gate antes de Analytics.

---

## O que está concluído

### ETAPA 0 — Limpeza da Casa + Dossiê Mestre

**Status: concluída.**

Entregas:

- Dossiê Mestre;
- arquitetura real Cloudflare documentada;
- plano oficial de evolução;
- README reconciliado;
- roadmap Beta arquivado como histórico;
- auditoria da Etapa 0;
- `.gitignore` reforçado;
- cadeia de produção mapeada;
- limite efetivo de 20 usuários no engajamento confirmado;
- distinção entre produção Cloudflare e legado local documentada.

Pendência técnica herdada:

```text
.venv ainda versionada
```

A remoção deve ser feita em operação Git dedicada, não misturada com mudança funcional.

---

## Próximo trabalho obrigatório

Antes da Etapa 1:

```text
GATE — validar engajamento proativo em produção/controlado
```

Critérios mínimos:

1. usuário comum consulta `Onde está o ônibus?` durante bloco ativo;
2. não ocorre nova confirmação durante a janela esperada;
3. cron encontra candidato;
4. convite chega;
5. `Sim, marcar ponto` abre o fluxo correto;
6. `Não vi` é consumido corretamente;
7. convite expira após 3 min;
8. uma nova confirmação confiável reinicia a lacuna;
9. registrar teste de regressão para o comportamento essencial.

Se falhar, corrigir antes de Analytics.

---

## Próxima etapa funcional

```text
ETAPA 1 — Fundação de Analytics
STATUS: não iniciada
```

Objetivo:

- usuários únicos;
- primeira interação;
- última interação;
- total de interações;
- consultas de localização;
- confirmações;
- eventos Principal/Micro;
- base para painel administrativo de estatísticas.

Regra obrigatória:

```text
falha de analytics nunca pode impedir o funcionamento normal do BUSIVS
```

---

## Direção futura já decidida

Na etapa de automação física, a direção conceitual preferida é:

```text
ESP32 + GPS + Wi-Fi institucional + geofences
```

O dispositivo ficaria embarcado/alimentado no veículo e combinaria evidência de GPS com presença em redes institucionais conhecidas. Isso é planejamento futuro e não deve ser antecipado antes das etapas atuais.

---

## Ao retomar o projeto

Leia nesta ordem:

1. `docs/GUIA_CONTINUIDADE_IA.md`;
2. `CONTINUIDADE.md`;
3. `docs/DOSSIE_MESTRE_BUSIVS.md`;
4. `docs/PLANO_EVOLUCAO_BUSIVS.md`;
5. `docs/BLOCOS_OPERACIONAIS.md`;
6. `docs/FLUXO_TELEGRAM.md`;
7. `docs/ARQUITETURA.md`;
8. `cloudflare/README.md`;
9. arquivos e testes da etapa em execução.
