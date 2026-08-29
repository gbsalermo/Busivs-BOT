# CONTINUIDADE — BUSIVS BOT

Documento curto para retomar o desenvolvimento rapidamente.

> Atualizado em 28/08/2026 durante a Etapa 0 — Limpeza da Casa + Dossiê Mestre.

## Estado atual

Produção:

```text
main -> Cloudflare Workers + Telegram Webhook + Durable Object
```

Branch de limpeza em andamento:

```text
chore/etapa-0-limpeza-dossie
```

Esta branch foi criada a partir do estado atual da `main` e não deve ser tratada como produção até validação/merge.

## Fonte de verdade

A partir desta etapa, regras de negócio e arquitetura não ficam mais concentradas neste arquivo.

Consultar primeiro:

```text
docs/DOSSIE_MESTRE_BUSIVS.md
```

Ele contém:

- arquitetura efetiva;
- camada externa Cloudflare;
- cadeia interna Python;
- Principal e Micro;
- regras de volta/bloco;
- RU, Biblioteca e Garagem;
- antiteleporte e estado não confiável;
- engajamento colaborativo;
- arquivos sensíveis;
- política de limpeza/refatoração;
- testes mínimos antes de mudanças estruturais.

Plano futuro:

```text
docs/PLANO_EVOLUCAO_BUSIVS.md
```

Arquitetura resumida:

```text
docs/ARQUITETURA.md
```

---

## Produção efetiva

Arquivo externo de configuração:

```text
cloudflare/wrangler.jsonc
```

Entrypoint configurado:

```text
cloudflare/src/entry_engajamento_final.py
```

Configuração relevante:

```text
Worker: busivs-bot
Cron: * * * * *
Durable Object binding: BUS_STATE
class: BusState
storage: sqlite
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

Não remover módulos `entry_*` olhando apenas o nome. Existem heranças e imports auxiliares entre camadas.

---

## Princípios operacionais preservados

```text
confirmação confiável > inferência pelo trajeto > horário
```

Regras centrais:

1. horário é referência de volta, não prova automática de posição;
2. dentro de um bloco, relógio sozinho não troca a volta;
3. fim real de bloco pode encerrar o contexto e impedir vazamento para o bloco seguinte;
4. RU confiável encerra a volta, mas não inicia a próxima sozinho;
5. nova volta pode ser reconhecida pela sequência real da rota;
6. Biblioteca é ambígua e depende de contexto;
7. salto suspeito não é bloqueado: vira indicação não confiável;
8. indicação suspeita não substitui estado confiável;
9. Principal e Micro permanecem independentes;
10. última volta mantém percurso de retorno sentido Garagem sem esconder os pontos ainda atendidos.

Detalhes completos estão no Dossiê Mestre.

---

## Engajamento colaborativo

A camada final de produção mantém pedidos automáticos de confirmação.

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

Limite efetivo atual:

```text
até 20 usuários por lote
```

Observação técnica: `entry_engajamento.py` mantém constante-base 10, mas `entry_engajamento_final.py` sobrescreve `_eng.MAX_CONVIDADOS = 20`. Portanto o comportamento efetivo do Worker é 20.

---

## Etapa 0 — o que já foi feito

Na branch `chore/etapa-0-limpeza-dossie`:

- criado `docs/DOSSIE_MESTRE_BUSIVS.md`;
- atualizado `docs/ARQUITETURA.md` para a arquitetura Cloudflare real;
- criado `docs/PLANO_EVOLUCAO_BUSIVS.md`;
- ampliado `.gitignore` para Python, ambientes virtuais, Wrangler, IDE e logs;
- identificado que `.venv` está versionada no histórico/repositório;
- identificada documentação antiga que ainda descrevia arquitetura pré-Cloudflare;
- mapeada a cadeia efetiva do entrypoint de produção;
- confirmada a diferença entre constante-base de engajamento e override final para 20.

Nenhuma regra de localização, rota, bloco, Micro, webhook ou Durable Object foi modificada durante esta limpeza documental.

---

## Pendências da Etapa 0

Antes de merge:

1. revisar `README.md` para apontar para o Dossiê e remover informações antigas;
2. registrar formalmente o inventário de arquivos/documentos históricos;
3. não remover `.venv` em centenas de chamadas pela API — fazer limpeza física em operação Git própria;
4. não consolidar `entry_*` sem testes de regressão;
5. comparar branch com `main` e confirmar que não houve alteração funcional acidental.

---

## Próxima etapa após a limpeza

```text
ETAPA 1 — Fundação de Analytics
```

Objetivo inicial:

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

Ordem recomendada de leitura:

1. `CONTINUIDADE.md`;
2. `docs/DOSSIE_MESTRE_BUSIVS.md`;
3. `docs/PLANO_EVOLUCAO_BUSIVS.md`;
4. `docs/ARQUITETURA.md`;
5. arquivos específicos da etapa em execução.
