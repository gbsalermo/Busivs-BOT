# CONTINUIDADE — BUSIVS BOT

Documento curto para retomar o desenvolvimento rapidamente.

> Atualizado em 28/08/2026 durante a Etapa 0 — Limpeza da Casa + Dossiê Mestre.

## Estado atual

Produção:

```text
main -> Cloudflare Workers + Telegram Webhook + Durable Object
```

Branch da Etapa 0:

```text
chore/etapa-0-limpeza-dossie
```

A branch nasceu do estado atual da `main` e ainda não deve ser tratada como produção até validação/merge.

## Fonte de verdade

Regras permanentes e arquitetura:

```text
docs/DOSSIE_MESTRE_BUSIVS.md
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
- administrador não entra normalmente no lote coletivo.

Limite efetivo:

```text
até 20 usuários por lote
```

`entry_engajamento.py` mantém constante-base 10, mas `entry_engajamento_final.py` sobrescreve `_eng.MAX_CONVIDADOS = 20`; portanto o Worker efetivo usa 20.

---

## Etapa 0 — concluído na branch

Foi realizado:

- criação do Dossiê Mestre;
- atualização da arquitetura para Cloudflare real;
- criação do plano oficial de evolução;
- atualização do README;
- transformação deste arquivo em continuidade curta;
- arquivamento documental do roadmap Beta antigo;
- criação da auditoria da Etapa 0;
- reforço do `.gitignore`;
- identificação da `.venv` versionada;
- mapeamento da cadeia efetiva de produção;
- confirmação do override efetivo de 20 usuários no engajamento.

Nenhuma regra funcional de localização, rota, bloco, Micro, webhook, cron ou Durable Object foi alterada durante esta limpeza.

### Mantido propositalmente para operação separada

```text
remoção física da .venv já versionada
```

Motivo: é mais seguro executar uma limpeza Git dedicada (`git rm -r --cached .venv`) do que centenas de deleções isoladas pela API.

Também não foram consolidadas/removidas camadas `entry_*`; isso exigirá testes de regressão antes.

---

## Próxima etapa

Depois de validar/mergear a Etapa 0:

```text
ETAPA 1 — Fundação de Analytics
```

Objetivo:

- usuários únicos;
- interações;
- consultas de localização;
- confirmações;
- eventos Principal/Micro;
- base para painel administrativo de estatísticas.

Regra obrigatória:

```text
falha de analytics nunca pode impedir o funcionamento normal do BUSIVS
```

---

## Ao retomar o projeto

Leia nesta ordem:

1. `CONTINUIDADE.md`;
2. `docs/DOSSIE_MESTRE_BUSIVS.md`;
3. `docs/PLANO_EVOLUCAO_BUSIVS.md`;
4. `docs/AUDITORIA_ETAPA_0.md`;
5. `docs/ARQUITETURA.md`;
6. arquivos específicos da etapa em execução.
