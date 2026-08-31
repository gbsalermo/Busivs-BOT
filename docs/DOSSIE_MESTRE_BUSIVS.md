# Dossiê Mestre — BUSIVS BOT

> Fonte de verdade arquitetural e de regras de negócio do BUSIVS. Revisado em 31/08/2026 com base na produção Cloudflare, documentação existente e decisões recentes.

## 1. Propósito

O BUSIVS é um bot comunitário no Telegram para reduzir a incerteza sobre a posição e a operação do Circular da UFRB — Campus Cruz das Almas.

O sistema atual não possui rastreamento GPS nativo. Ele combina:

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

### 2.1 Cloudflare

Produção roda em Cloudflare Workers for Python.

Arquivo de configuração:

```text
cloudflare/wrangler.jsonc
```

Configuração efetiva:

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

### 2.2 Cadeia Python

A produção entra por:

```text
cloudflare/src/entry_engajamento_final.py
```

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

Além da herança, existem imports auxiliares diretos. Não remover uma camada apenas porque ela não parece ser o entrypoint final.

`entry_engajamento_final.py` reaproveita explicitamente os métodos de estado do engajamento e mantém como base funcional a cadeia final de consistência/antiteleporte.

### 2.3 Produção x base histórica

A pasta:

```text
cloudflare/
```

é a implementação efetiva de produção.

A pasta raiz:

```text
src/
```

contém a base histórica/local por polling. Ela pode ser usada como referência ou para testes antigos, mas uma alteração ali não muda automaticamente o Worker de produção.

---

## 3. Persistência

O estado operacional é compartilhado via Durable Object / SQLite.

A persistência faz parte do comportamento do produto. Mudanças em:

```text
BusState
chaves do storage
formatos JSON persistidos
binding BUS_STATE
class_name
```

devem ser tratadas como mudanças potencialmente incompatíveis com produção.

Nunca fazer migração destrutiva apenas para simplificar código.

---

## 4. Regra de referência de volta

- horário identifica uma referência de volta;
- relógio sozinho não encerra uma volta intermediária;
- relógio sozinho não inicia a próxima volta dentro do mesmo bloco;
- referência muda por evidência da rota, ajuste administrativo ou fechamento/abertura real de bloco.

Exemplo:

```text
referência 11:30
12:00 sem nova evidência
=> continua associado à referência 11:30
```

Quando o ônibus chega ao RU e a próxima referência oficial existe, o sistema pode deixar essa próxima referência preparada, mas ela não deve ser tratada como posição ativa apenas porque o relógio avançou.

---

## 5. Fim de bloco

Dentro do bloco, horário tem autoridade limitada.

No fim real do bloco, o relógio recupera autoridade para impedir que uma referência velha atravesse indefinidamente para o bloco seguinte.

Regra conceitual:

```text
dentro do bloco
=> preservar evidência real mesmo com atraso

limite real do bloco / início de outro bloco
=> encerrar contexto velho quando não houver evidência compatível
```

Quando um novo bloco já começou, confirmação compatível com esse bloco pode limpar o histórico anterior e iniciar um contexto novo.

RU continua ambíguo nessa transição porque pode representar chegada da volta anterior ou espera para nova saída.

---

## 6. RU

Confirmação confiável no RU significa chegada/fim da volta atual.

RU não inicia automaticamente a próxima volta.

Uma nova volta pode ser reconhecida sem RU explícito quando a sequência de pontos, combinada com uma saída oficial posterior, comprovar reinício do percurso.

---

## 7. Biblioteca

Biblioteca é ambígua porque aparece na ida e no retorno.

Nunca decidir sentido somente pelo ID `biblioteca`.

Usar:

- sequência de rota;
- último estado confiável;
- referência de volta;
- contexto do bloco;
- tempo/contexto específico de retorno quando aplicável.

---

## 8. Última volta / retorno / Garagem

Na última volta de um bloco:

- não inventar nova volta depois da última referência oficial;
- informar **percurso de retorno sentido Garagem**;
- não dizer simplesmente “retornando para a Garagem” quando ainda existem pontos úteis no caminho, pois isso pode sugerir que o ônibus não atenderá mais ninguém;
- Fitotecnia/Solos e demais pontos compatíveis podem continuar relevantes no retorno dependendo do fluxo real;
- encerramento administrativo por Garagem fecha o bloco;
- depois do fechamento real, `Onde está o ônibus?` deve informar Garagem/próxima saída em vez de manter uma confirmação antiga como se ainda estivesse ativa.

---

## 9. Confiabilidade e antiteleporte

Não existe bloqueio geral por tempo entre todos os pontos.

Saltos muito característicos podem exigir confirmação adicional.

Exemplos historicamente protegidos:

```text
Fitotecnia -> Biblioteca : < 1 min
Biblioteca -> Portão 1   : < 2 min
Portão 1 -> Biblioteca   : < 1 min
Portão 1 -> RU           : < 2 min
```

Fluxo:

```text
salto suspeito
-> “Você tem certeza?”
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

Nova evidência confiável pode resolver/descartar a suspeita anterior.

As mesmas regras conceituais se aplicam ao Principal e ao Micro.

---

## 10. Circular Principal

Rota conceitual:

```text
RU
-> Fitotecnia
-> Solos / NEAS / Eng. Florestal
-> Pavilhão I
-> Biblioteca
-> Pavilhão II
-> Pavilhão de Engenharia (opcional)
-> Portão 2
-> Ponto Externo I / Alex
-> Ponto Externo II / Canaã
-> Portão 1
-> Biblioteca
-> Torre / COTEC (opcional)
-> RU
```

A rota e os rótulos oficiais devem ser conferidos em:

```text
cloudflare/src/dados.py
```

antes de qualquer mudança.

### 10.1 Blocos configurados

```text
06:25–07:55
09:35–10:00
11:30–12:20
13:00–14:00
15:35–16:00
17:30–18:15
20:00–20:00  [experimental]
20:40–20:40
21:40–21:40
22:30–22:30
```

A referência de **20:00** existe no código como experimental:

```text
origem: Garagem
previsão Portão 1: 20:10–20:15
observação: pode não ocorrer; baseada em rotina anterior
fechamento explícito do bloco: 20:25
```

Ela não deve ser documentada como volta garantida.

Os blocos 20:00, 20:40, 21:40 e 22:30 são independentes.

---

## 11. Micro-ônibus

O Micro é reforço e possui estado separado do Principal.

Ele segue a mesma filosofia colaborativa:

- ponto real conduz o estado;
- relógio não troca volta sozinho;
- RU confiável encerra a volta;
- nova volta depende de evidência de rota/contexto;
- suspeitas permanecem separadas do estado confiável;
- sessão não deve atravessar bloco indevidamente.

Referências configuradas:

```text
07:25 — Garagem
07:40 — RU/Residências
07:55 — RU/Residências

11:20 — Garagem
11:55 — RU/Residências
12:20 — RU/Residências
```

Regras de ativação e sessão devem ser conferidas em `micro.py`, `entry_micro_flex.py` e camadas finais.

Tempo desde ativação não deve ser usado como prova de posição.

---

## 12. Engajamento colaborativo

Objetivo: pedir ajuda quando há silêncio de confirmação, sem transformar o bot em spam.

Regras consolidadas:

- candidato entra ao consultar `Onde está o ônibus?`;
- somente usuários comuns entram normalmente como candidatos;
- apenas durante operação válida do Principal;
- silêncio conta desde a última confirmação confiável ou, se inexistente, desde a referência da saída;
- indicação suspeita não reinicia o contador;
- normal: primeiro lote ~+5 min;
- pico: primeiro lote ~+10 min;
- segundo lote ~+15 min normal / ~+20 min pico;
- último autor confiável pode receber fallback individual intermediário;
- máximo de 2 lotes coletivos por volta;
- nova confirmação confiável reinicia a lacuna, mas não cria cota infinita de lotes;
- convite expira em 3 min;
- respostas: `📍 Sim, marcar ponto` ou `❌ Não vi`.

### 12.1 Limite efetivo

Decisão de negócio atual:

```text
até 20 candidatos por lote
```

A camada-base `entry_engajamento.py` ainda possui:

```text
MAX_CONVIDADOS = 10
```

mas `entry_engajamento_final.py` executa:

```python
_eng.MAX_CONVIDADOS = 20
```

O comportamento efetivo do Worker é 20. Preservar até futura consolidação controlada.

### 12.2 Incidente de 25/08/2026

Em uso real foi observado que os pedidos proativos não chegavam.

A investigação mostrou que o Worker ainda estava configurado com:

```text
main: src/entry_consistencia.py
```

portanto a camada final de engajamento não era o entrypoint externo.

Correções:

```text
66ce4f3 — reintegra avisos colaborativos ao entrypoint final
020f09c — wrangler passa a usar entry_engajamento_final.py
2a14042 — limite efetivo elevado para 20
```

Situação atual:

```text
código corrigido
cron ativo a cada minuto
validação real/controlada pós-correção ainda necessária
```

Também existe uma lacuna de testes: a suíte Cloudflare cobre regras de rota/bloco, mas não possui cobertura equivalente do ciclo completo cron -> seleção -> convite -> resposta/expiração.

Isso é um **gate operacional** antes da Etapa 1.

---

## 13. Interface Telegram atual

A UX principal é por botões inline.

Usuário comum possui:

```text
🚌 Onde está o ônibus?
📍 Informar ponto atual        [quando há operação]
⏰ Próximos horários
📋 Listar horários
🚐 Confirmar que o micro está rodando / Micro em operação
❓ Ajuda
```

Na Ajuda:

```text
🗺️ Rota atual
📖 Dicas para uso do BOT
💬 Enviar feedback
```

Não existe autenticação obrigatória por e-mail institucional no fluxo atual.

NFC/deep links por ponto não estão implementados em produção.

---

## 14. Administração

Controles administrativos não devem poluir o menu comum.

Funções atuais incluem:

```text
Escolher volta de referência do bloco
Garagem / Encerrar bloco
Correção de ponto/sentido por controles administrativos
Correção/gestão do Micro
Avisos operacionais
```

A seleção de referência substituiu o antigo conceito de simplesmente “voltar para a volta anterior”, permitindo escolher explicitamente a volta desejada dentro do bloco.

Ajustes manuais têm prioridade operacional, mas não devem apagar estado confiável sem necessidade.

---

## 15. Avisos operacionais

Avisos pertencem a um contexto operacional e não devem permanecer indefinidamente.

Princípios:

- aviso velho não pode atravessar blocos sem intenção;
- ocorrência continuada deve ser republicada quando necessário;
- avisos podem afetar a mensagem de localização, por exemplo atraso, chuva, quebra, portão fechado ou rota alterada;
- administração publica/remove avisos pelo menu restrito.

Detalhes de expiração ficam em `docs/BLOCOS_OPERACIONAIS.md` e código específico.

---

## 16. Feedback

A área de Ajuda possui envio de feedback em produção.

Fluxo atual:

```text
Ajuda
-> Enviar feedback
-> usuário responde ao prompt
-> mensagem é encaminhada ao administrador
```

Evolução prevista: categorias estruturadas e consulta administrativa dos feedbacks recentes.

---

## 17. Arquivos de alta sensibilidade

`cloudflare/wrangler.jsonc`
: entrypoint, cron e Durable Object. Alteração errada pode derrubar produção sem mudar regra de negócio.

`cloudflare/src/entry_engajamento_final.py`
: camada final exposta ao Cloudflare.

`cloudflare/src/entry_consistencia.py`
: coerência final de Principal/Micro e exibição.

`cloudflare/src/entry_antiteleporte.py`
: suspeitas, resolução por evidência e reinício de volta.

`cloudflare/src/registro_colaborativo.py`
: registro por rota sem depender do relógio do Principal.

`cloudflare/src/volta_referencia.py`
: referência persistente de volta.

`cloudflare/src/expiracao_volta.py`
: fechamento real do bloco.

`cloudflare/src/blocos_operacionais.py`
: regras compartilhadas de bloco/fechamento.

`cloudflare/src/transicao_bloco.py`
: troca limpa de contexto entre blocos.

`cloudflare/src/estado_bus.py`
: estado base e helpers históricos. Nem todo helper antigo representa a regra final.

`cloudflare/src/dados.py`
: horários, pontos, blocos e rota.

`cloudflare/src/micro.py` / `entry_micro_flex.py`
: faixa funcional, referência e sessão do Micro.

---

## 18. Política de limpeza/refatoração

O BUSIVS cresceu por camadas `entry_*`. Algumas implementações antigas ainda são importadas por camadas atuais.

Política obrigatória:

1. não apagar módulo apenas porque existe implementação mais nova;
2. provar que ele não aparece no grafo de imports/herança de produção;
3. identificar a regra de negócio que ele fornece;
4. criar teste de regressão;
5. validar Worker, webhook, cron, Principal, Micro e administração;
6. somente então remover/consolidar.

A dívida técnica existe, mas simplificação estrutural não tem prioridade sobre preservação funcional.

---

## 19. Testes

Existem duas regiões:

```text
tests/
-> base histórica/local

cloudflare/tests/
-> testes mais diretamente ligados às regras atuais de produção
```

Coberturas atuais incluem regras de:

- blocos operacionais;
- registro colaborativo;
- rota;
- RU/pós-RU;
- retorno à Garagem;
- noturno rápido;
- referência de volta;
- validações de rota.

Lacuna conhecida:

```text
engajamento proativo completo
cron -> candidatos -> convite -> consumo/expiração
```

Essa cobertura deve ser criada antes de mudanças profundas no engajamento.

---

## 20. Etapa 0

A Etapa 0 — Limpeza da Casa + Dossiê Mestre está concluída e já está incorporada à `main`.

Entregas consolidadas:

- Dossiê Mestre;
- README atual;
- arquitetura real Cloudflare;
- plano de evolução;
- auditoria;
- roadmap Beta marcado como histórico;
- `.gitignore` reforçado;
- cadeia de produção mapeada.

A `.venv` já versionada permanece como dívida técnica e deve ser removida do índice em operação Git dedicada.

---

## 21. Planejamento oficial

Próximo passo imediato:

```text
GATE OPERACIONAL
validar engajamento proativo pós-correção
+ adicionar regressão essencial
```

Depois:

```text
ETAPA 1 — Fundação de Analytics
```

Analytics deve ser observacional: falha de métrica nunca pode impedir resposta, confirmação ou funcionamento do BUSIVS.

As demais etapas estão em `docs/PLANO_EVOLUCAO_BUSIVS.md`.

---

## 22. Automação física futura

A direção conceitual preferida para a Etapa 8 é um dispositivo embarcado, alimentado no ônibus, combinando:

```text
ESP32
+ GPS
+ Wi-Fi institucional
+ geofences/pontos conhecidos
```

Hipótese de evidência:

```text
GPS entra no raio do ponto
+ conexão com rede institucional conhecida
=> evidência automática com confiança maior
```

O dispositivo deve poder alternar entre redes institucionais configuradas e nunca deve versionar credenciais reais.

Rastreadores veiculares comerciais foram considerados, mas a direção atual favorece a solução embarcada própria por facilitar integração com as regras do BUSIVS.

Modelo desejado:

```text
evidência automática
+ confirmação colaborativa
+ inferência de rota
```

Automação física complementa o modelo humano; não elimina imediatamente a colaboração.

---

## 23. Hierarquia documental

```text
docs/GUIA_CONTINUIDADE_IA.md
= handoff para outra IA

CONTINUIDADE.md
= status atual + próximo trabalho

docs/DOSSIE_MESTRE_BUSIVS.md
= fonte de verdade de regras e decisões

docs/PLANO_EVOLUCAO_BUSIVS.md
= etapas oficiais

docs/ARQUITETURA.md
= visão técnica resumida

docs/BLOCOS_OPERACIONAIS.md
= regras de blocos

docs/FLUXO_TELEGRAM.md
= UX atual

docs/ROADMAP_BETA.md
= histórico
```

Quando houver conflito entre documento antigo e código efetivo auditado, não alterar o código automaticamente para combinar com o documento. Primeiro identificar qual comportamento foi aprovado mais recentemente.
