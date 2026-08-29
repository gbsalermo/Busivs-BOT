# Dossiê Mestre — BUSIVS BOT

> Fonte de verdade arquitetural e de regras de negócio do BUSIVS. Atualizado em 28/08/2026 durante a Etapa 0 — Limpeza da Casa.

## 1. Propósito

O BUSIVS é um bot comunitário no Telegram para reduzir a incerteza sobre a posição e a operação do Circular da UFRB — Campus Cruz das Almas.

O sistema não possui rastreamento GPS nativo. Ele combina:

```text
confirmações colaborativas
+ sequência física da rota
+ contexto da volta/bloco
+ horários oficiais como referência
+ inferências controladas
```

Princípio de autoridade:

```text
confirmação confiável > inferência pelo trajeto > horário
```

Horário é referência operacional. Nunca deve ser tratado isoladamente como prova de posição.

---

## 2. Arquitetura de produção

### 2.1 Camada externa — Cloudflare

Produção roda em Cloudflare Workers para Python.

Arquivo de configuração:

```text
cloudflare/wrangler.jsonc
```

Configuração efetiva auditada em 28/08/2026:

```text
Worker: busivs-bot
Entrypoint: src/entry_engajamento_final.py
Compatibilidade: python_workers
Cron: * * * * *
Durable Object binding: BUS_STATE
Durable Object class: BusState
Storage: SQLite no Durable Object
```

Secrets esperados:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
ADMIN_TELEGRAM_ID
```

Nunca versionar valores reais.

### 2.2 Camada interna — cadeia Python

A produção entra por:

```text
entry_engajamento_final.py
```

Cadeia principal de herança/imports observada:

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

Além da herança, existem imports auxiliares diretos entre módulos. Por isso, não remover uma camada apenas porque ela não parece ser o entrypoint final.

`entry_engajamento_final.py` também reaproveita explicitamente métodos de `entry_engajamento.BusState`, mantendo engajamento e cron sem substituir as regras finais de consistência/antiteleporte.

### 2.3 Estado persistente

O estado operacional é compartilhado via Durable Object / SQLite.

A persistência faz parte do comportamento do produto. Mudanças em `BusState`, chaves de storage, formatos persistidos, binding ou `class_name` devem ser tratadas como mudanças potencialmente incompatíveis com produção.

---

## 3. Regras de negócio que não podem ser quebradas

### 3.1 Referência de volta

- horário identifica referência de volta;
- relógio sozinho não encerra uma volta intermediária;
- relógio sozinho não inicia a próxima volta dentro do mesmo bloco;
- referência muda por evidência de rota, ajuste administrativo ou fechamento/abertura real de bloco.

Exemplo:

```text
referência 11:30
12:00 sem nova evidência
=> continua associado à referência 11:30
```

### 3.2 Fim de bloco

No fim real de um bloco, o relógio volta a ter autoridade para encerrar o contexto operacional e impedir que uma referência velha invada o próximo bloco.

### 3.3 RU

Confirmação confiável no RU significa chegada/fim da volta atual.

RU não inicia automaticamente a próxima volta.

Uma nova volta pode ser reconhecida sem RU explícito quando a sequência de pontos comprovar reinício do percurso.

### 3.4 Última volta / Garagem

Na última volta do bloco:

- não inventar nova volta depois da última referência oficial;
- informar percurso de retorno sentido Garagem;
- lembrar que ainda existem pontos úteis no retorno;
- Fitotecnia/Solos podem fazer parte do caminho para a Garagem;
- encerramento administrativo por Garagem fecha o bloco.

### 3.5 Biblioteca

Biblioteca é ambígua porque aparece na ida e no retorno.

Nunca decidir sentido somente pelo ID `biblioteca`. Usar sequência de rota, estado confiável e contexto operacional.

---

## 4. Confiabilidade e antiteleporte

Não existe bloqueio geral por tempo entre pontos.

Saltos muito característicos podem exigir confirmação adicional:

```text
Fitotecnia -> Biblioteca : < 1 min
Biblioteca -> Portão 1   : < 2 min
Portão 1 -> Biblioteca   : < 1 min
Portão 1 -> RU           : < 2 min
```

Fluxo:

```text
salto suspeito
-> "Você tem certeza?"
-> cancelar = mantém estado confiável anterior
-> confirmar = salva indicação NÃO CONFIÁVEL
```

Uma indicação não confiável:

- não encerra volta;
- não inicia volta;
- não substitui a última localização confiável;
- não força sentido definitivo;
- não dispara Garagem;
- não vira base obrigatória para o próximo registro.

Nova evidência confiável pode descartar a suspeita anterior.

As mesmas regras conceituais se aplicam ao Principal e ao Micro.

---

## 5. Circular Principal

Rota conceitual de ida:

```text
RU
-> Fitotecnia
-> Solos / NEAS / Eng. Florestal
-> Pavilhão I
-> Biblioteca
-> Pavilhão II
-> Pavilhão de Engenharia (opcional)
-> Portão 2
-> Alex
-> Canaã
-> Portão 1
```

Retorno:

```text
Portão 1
-> Biblioteca
-> Torre / COTEC (opcional)
-> RU
```

A rota e os rótulos oficiais devem ser conferidos em `cloudflare/src/dados.py` antes de qualquer mudança.

---

## 6. Micro-ônibus

O Micro é reforço e possui estado separado do Principal.

Ele segue a mesma filosofia colaborativa:

- ponto real conduz o estado;
- relógio não troca volta sozinho;
- RU confiável encerra a volta;
- nova volta depende de evidência de rota;
- suspeitas permanecem separadas do estado confiável.

Referências documentadas atualmente:

```text
07:25 — Garagem
07:40 — RU/Residências
07:55 — RU/Residências

11:20 — Garagem
11:55 — RU/Residências
12:20 — RU/Residências
```

Regras de ativação e sessão devem ser conferidas em `micro.py` e `entry_micro_flex.py`. Tempo desde ativação não deve ser usado como prova de posição.

---

## 7. Engajamento colaborativo

Objetivo: pedir ajuda quando há silêncio de confirmação, sem transformar o bot em spam.

Regras consolidadas:

- candidato entra ao consultar `Onde está o ônibus?`;
- apenas durante operação válida do Principal;
- silêncio conta desde a última confirmação confiável ou, se inexistente, desde a referência da saída;
- indicação suspeita não reinicia o contador;
- normal: primeiro lote ~+5 min;
- pico: primeiro lote ~+10 min;
- segundo lote ~+15 min normal / ~+20 min pico;
- último autor confiável pode receber fallback individual intermediário;
- máximo de 2 lotes coletivos por volta;
- nova confirmação confiável reinicia a lacuna de silêncio, mas não cria cota infinita de lotes;
- convite expira em 3 min;
- respostas: `Sim, marcar ponto` ou `Não vi`.

### Limite de destinatários

Decisão de negócio atual:

```text
até 20 candidatos por lote
```

A camada-base `entry_engajamento.py` ainda possui `MAX_CONVIDADOS = 10`, porém a camada final de produção executa:

```python
_eng.MAX_CONVIDADOS = 20
```

Logo, o comportamento efetivo do Worker é 20. Esta sobreposição deve ser preservada até uma futura consolidação controlada das camadas.

---

## 8. Administração

Controles administrativos não devem poluir o menu comum.

Funções atuais incluem:

```text
Escolher volta de referência
Corrigir ponto / sentido
Corrigir Micro
Garagem / Encerrar bloco
Avisos operacionais
```

Ajustes manuais têm prioridade operacional, mas não devem apagar estado confiável sem necessidade.

---

## 9. Feedback

A área de Ajuda possui fluxo para envio de feedback.

Evolução prevista: categorias estruturadas e consulta administrativa dos feedbacks recentes.

---

## 10. Arquivos de alta sensibilidade

`cloudflare/wrangler.jsonc`
: entrypoint, cron e Durable Object. Alteração errada pode derrubar produção sem mudar uma única regra de negócio.

`cloudflare/src/entry_engajamento_final.py`
: camada final atual de produção.

`cloudflare/src/entry_consistencia.py`
: coerência final de Principal/Micro.

`cloudflare/src/entry_antiteleporte.py`
: suspeitas, resolução por evidência e reinício de volta.

`cloudflare/src/registro_colaborativo.py`
: registro por rota sem depender do relógio do Principal.

`cloudflare/src/volta_referencia.py`
: referência persistente de volta.

`cloudflare/src/expiracao_volta.py`
: fechamento real do bloco.

`cloudflare/src/estado_bus.py`
: estado base e helpers históricos. Nem todo helper antigo representa a regra final.

`cloudflare/src/dados.py`
: horários, pontos, blocos e rota.

`cloudflare/src/micro.py` / `entry_micro_flex.py`
: faixa funcional, referência e sessão do Micro.

---

## 11. Política de limpeza

O BUSIVS cresceu por camadas `entry_*`. Algumas implementações antigas ainda são importadas por camadas atuais.

Política obrigatória:

1. não apagar módulo apenas porque existe implementação mais nova;
2. primeiro provar que ele não aparece no grafo de imports de produção;
3. identificar a regra de negócio que ele fornece;
4. criar teste de regressão;
5. validar Worker, webhook, cron, Principal e Micro;
6. somente então remover/consolidar.

A Etapa 0 prioriza limpeza documental e organizacional. Remoção agressiva das camadas fica para refatoração específica com cobertura de testes.

---

## 12. Achados da Etapa 0

### 12.1 `.venv` versionada

O repositório contém ambiente virtual versionado. O `.gitignore` original só ignorava `.env`.

O `.gitignore` foi ampliado para impedir novos arquivos locais, caches, `.venv`, `.wrangler`, arquivos de IDE e logs.

A remoção física da `.venv` já versionada deve ser feita em operação própria, preferencialmente via Git local, evitando centenas de deleções isoladas pela API.

### 12.2 Arquitetura antiga na documentação

`docs/ARQUITETURA.md` descrevia uma arquitetura planejada antiga com `bot.py`, JSON e SQLite local. Foi substituída pela arquitetura real Cloudflare + Durable Object.

### 12.3 `CONTINUIDADE.md` desatualizado

O arquivo ainda cita `entry_consistencia.py` como entrypoint e contém informações antigas sobre engajamento. Ele deve ser reconciliado com este Dossiê antes de a branch ser promovida a `main`.

### 12.4 Camada externa x interna

A configuração Cloudflare e a cadeia Python devem ser auditadas separadamente. O fato de uma regra existir em um módulo não significa que ela esteja exposta pelo entrypoint configurado no Worker.

---

## 13. Testes mínimos antes de merge estrutural

Principal:

1. `Onde está o ônibus?` mantém estado coerente;
2. marcação confiável atualiza posição;
3. salto suspeito não substitui estado confiável;
4. evidência posterior resolve suspeita;
5. RU encerra volta sem iniciar próxima sozinho;
6. reinício por rota funciona sem RU explícito;
7. fim de bloco impede referência antiga de invadir o bloco seguinte;
8. Garagem encerra corretamente o bloco.

Micro:

1. ativação somente em contexto permitido;
2. Principal e Micro permanecem independentes;
3. referência não avança só pelo relógio;
4. suspeitas seguem a mesma separação de confiabilidade;
5. sessão não atravessa bloco indevidamente.

Engajamento:

1. consulta de usuário comum gera candidatura;
2. admin não entra por engano no lote normal;
3. cron dispara quando aplicável;
4. limite efetivo é de até 20 candidatos;
5. máximo de 2 lotes coletivos por volta;
6. nova confirmação reinicia a lacuna;
7. convite expira em 3 min.

Cloudflare:

1. `wrangler.jsonc` aponta para `entry_engajamento_final.py`;
2. `BusState` exportado continua compatível com o Durable Object existente;
3. webhook continua respondendo;
4. cron continua ativo.

---

## 14. Hierarquia documental

```text
DOSSIE_MESTRE_BUSIVS.md
= fonte de verdade de arquitetura e regras

CONTINUIDADE.md
= status atual + próxima etapa

PLANO_EVOLUCAO_BUSIVS.md
= etapas futuras

ARQUITETURA.md
= visão técnica resumida

Demais docs
= detalhes específicos ou histórico
```

Quando houver conflito entre documento antigo e código efetivo auditado, não alterar o código automaticamente para combinar com o documento. Primeiro identificar qual comportamento foi aprovado mais recentemente.

---

## 15. Próxima fase após a Etapa 0

A próxima etapa é a Fundação de Analytics:

- usuários únicos;
- interações;
- consultas de localização;
- confirmações;
- métricas por volta;
- efetividade dos avisos;
- painel administrativo.

Analytics deve ser observacional: falha de métrica nunca pode impedir resposta, confirmação ou funcionamento operacional do BUSIVS.
