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

Nunca versionar os valores reais.

### 2.2 Camada interna — cadeia Python

A produção entra por:

```text
entry_engajamento_final.py
```

A cadeia funcional principal observada é:

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

`entry_engajamento_final.py` também reaproveita explicitamente métodos de `entry_engajamento.BusState` para manter o engajamento ativo sem substituir as regras finais de consistência/antiteleporte.

### 2.3 Estado persistente

O estado operacional é compartilhado via Durable Object / SQLite.

A persistência é parte do comportamento do produto. Alterações em chaves de storage, formato de estado ou classe `BusState` devem ser tratadas como mudanças de migração, não como simples refatoração.

---

## 3. Regras que não podem ser quebradas

### 3.1 Referência de volta

- horário identifica referência de volta;
- relógio sozinho não encerra uma volta intermediária;
- relógio sozinho não inicia a próxima volta dentro do mesmo bloco;
- referência muda por evidência de rota, ajuste administrativo ou fechamento/abertura real de bloco.

Exemplo:

```text
referência 11:30
12:00 sem nova evidência
=> a volta continua associada à referência 11:30
```

### 3.2 Fim de bloco

No fim real de um bloco, o relógio volta a ter autoridade para encerrar o contexto operacional e impedir que uma referência velha invada o próximo bloco.

Uma volta antiga nunca deve permanecer como referência ativa depois que o novo bloco já deveria ter iniciado operacionalmente.

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

Biblioteca é um ponto ambíguo porque aparece na ida e no retorno.

Nunca decidir sentido somente pelo ID `biblioteca`.

Usar sequência de rota, estado confiável e contexto operacional.

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

O Principal é o veículo de referência do BUSIVS.

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

A rota real e os rótulos oficiais devem ser conferidos em `cloudflare/src/dados.py` antes de qualquer mudança de nomenclatura.

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

Regra de ativação:

- usuário comum: somente na faixa funcional;
- antecedência operacional: cerca de 30 min antes da primeira referência;
- sessões extraordinárias fora da faixa, quando permitidas por administração, precisam de expiração controlada;
- não usar "tempo desde ativação" para inferir posição.

Sempre validar horários em `dados.py` e regras de sessão em `micro.py` / `entry_micro_flex.py` antes de editar documentação ou comportamento.

---

## 7. Engajamento colaborativo

Objetivo: pedir ajuda quando há silêncio de confirmação, sem transformar o bot em spam.

Regras consolidadas:

- candidato entra ao consultar `Onde está o ônibus?`;
- apenas durante operação válida do Principal;
- silêncio conta desde a última confirmação confiável ou, se inexistente, desde a referência da saída;
- indicação suspeita não reinicia o contador;
- horário normal: primeiro lote ~+5 min;
- pico: primeiro lote ~+10 min;
- segundo lote ~+15 min normal / ~+20 min pico;
- último autor confiável pode receber fallback individual intermediário;
- máximo de 2 lotes coletivos por volta;
- nova confirmação confiável reinicia a lacuna de silêncio, mas não cria cota infinita de lotes;
- convite expira em 3 min;
- respostas: `Sim, marcar ponto` ou `Não vi`.

Meta de produto aprovada: **até 20 candidatos por lote**.

### Atenção de auditoria

Durante a Etapa 0 foi encontrado `MAX_CONVIDADOS = 10` em `entry_engajamento.py`, apesar da decisão de negócio já ter sido alterada para 20. Esta divergência deve ser corrigida e validada antes de promover a branch de limpeza para produção.

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

Ajustes manuais têm prioridade operacional, mas não devem destruir histórico confiável sem necessidade.

---

## 9. Feedback

A área de Ajuda possui fluxo para envio de feedback.

Evolução prevista: categorizar feedbacks e permitir consulta administrativa estruturada.

---

## 10. Arquivos de alta sensibilidade

```text
cloudflare/wrangler.jsonc
```
Define entrypoint, cron e Durable Object. Alteração errada pode derrubar produção mesmo sem mudar regra de negócio.

```text
cloudflare/src/entry_engajamento_final.py
```
Camada final atual de produção.

```text
cloudflare/src/entry_consistencia.py
```
Coerência final de Principal/Micro.

```text
cloudflare/src/entry_antiteleporte.py
```
Suspeitas, evidência posterior e reinício por rota.

```text
cloudflare/src/registro_colaborativo.py
```
Registro por rota sem depender do relógio do Principal.

```text
cloudflare/src/volta_referencia.py
```
Persistência e troca de referência de volta.

```text
cloudflare/src/expiracao_volta.py
```
Fechamento operacional.

```text
cloudflare/src/estado_bus.py
```
Estado base e helpers históricos. Não assumir que todo helper ainda representa a regra final.

```text
cloudflare/src/dados.py
```
Horários, pontos e rota.

```text
cloudflare/src/micro.py
cloudflare/src/entry_micro_flex.py
```
Faixa funcional, referência e sessão do Micro.

---

## 11. Código legado e política de limpeza

O BUSIVS cresceu por camadas `entry_*`. Algumas camadas antigas ainda podem ser importadas por outras camadas atuais.

Política obrigatória:

1. não apagar módulo apenas porque existe uma implementação mais nova;
2. primeiro provar que ele não aparece no grafo de imports da produção;
3. depois criar teste de regressão para a regra coberta;
4. somente então remover/consolidar;
5. mudanças estruturais devem ser feitas em branch e nunca diretamente em produção.

Durante a Etapa 0, a limpeza de código deve ser predominantemente documental e organizacional. Consolidação física das camadas fica para uma refatoração posterior com testes.

---

## 12. Problemas estruturais identificados na Etapa 0

### 12.1 `.venv` versionada

O repositório contém ambiente virtual versionado. Isso não deve continuar.

O `.gitignore` foi ampliado para impedir novos arquivos locais, caches, `.venv`, `.wrangler` e artefatos de IDE.

A remoção física da `.venv` versionada deve ser feita em operação própria, preferencialmente localmente com Git, para evitar centenas de deleções isoladas pela API.

### 12.2 Documentação arquitetural antiga

`docs/ARQUITETURA.md` descrevia uma arquitetura planejada antiga (`bot.py`, JSON local e SQLite tradicional), diferente da produção Cloudflare atual. Ela deve apontar para a arquitetura auditada neste dossiê.

### 12.3 Documentação de continuidade desatualizada

O `CONTINUIDADE.md` ainda cita `entry_consistencia.py` como entrypoint de produção e contém regras antigas de engajamento. Antes de merge para `main`, o documento deve ser reconciliado com este dossiê.

---

## 13. Testes mínimos antes de qualquer merge estrutural

Principal:

1. consulta `Onde está o ônibus?` mantém estado coerente;
2. marcação confiável atualiza posição;
3. salto suspeito não substitui o confiável;
4. evidência posterior resolve suspeita;
5. RU encerra volta sem iniciar próxima sozinho;
6. reinício por Fitotecnia/Solos/Pav I funciona sem RU explícito;
7. fim de bloco impede referência antiga de invadir o seguinte;
8. Garagem encerra corretamente o bloco.

Micro:

1. ativação somente na faixa válida;
2. Principal e Micro permanecem independentes;
3. referência do Micro não avança só pelo relógio;
4. suspeitas seguem as mesmas regras de confiabilidade;
5. sessão não atravessa bloco indevidamente.

Engajamento:

1. consulta de usuário comum gera candidatura;
2. admin não entra por engano no lote normal;
3. cron roda sem confirmação recente;
4. limite de candidatos respeita a configuração vigente;
5. máximo de 2 lotes coletivos por volta;
6. nova confirmação reinicia a lacuna;
7. convite expira em 3 min.

Cloudflare:

1. `wrangler.jsonc` aponta para a camada final esperada;
2. `BusState` exportado continua compatível com Durable Object existente;
3. webhook do Telegram continua respondendo;
4. cron continua ativo.

---

## 14. Regra de documentação

Hierarquia documental recomendada:

```text
DOSSIE_MESTRE_BUSIVS.md
= fonte de verdade de arquitetura e regras

CONTINUIDADE.md
= onde o desenvolvimento parou + próxima etapa

PLANO_EVOLUCAO_BUSIVS.md
= etapas futuras e prioridades

ARQUITETURA.md
= visão técnica resumida

Demais docs
= detalhes específicos ou histórico
```

Quando houver conflito entre documentação antiga e código efetivo auditado, não alterar o código automaticamente para “combinar com o documento”. Primeiro identificar qual comportamento é o aprovado mais recente e então atualizar a documentação.

---

## 15. Próxima fase após Etapa 0

Depois da limpeza e validação documental, a próxima etapa é a Fundação de Analytics:

- usuários únicos;
- interações;
- consultas de localização;
- confirmações;
- métricas por volta;
- efetividade dos avisos de colaboração;
- painel administrativo de estatísticas.

Analytics deve ser observacional: falha de métrica nunca pode impedir resposta, confirmação ou funcionamento operacional do BUSIVS.
