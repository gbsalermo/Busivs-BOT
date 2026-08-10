# CONTINUIDADE - BUSIVS BOT

Documento de retomada rápida do projeto.

## Regra principal de desenvolvimento

> **O BUSIVS BOT deve ser simples e eficaz.**

Este é um projeto desenvolvido principalmente por **vibecoding**. Portanto, toda decisão técnica deve favorecer código pequeno, legível, fácil de testar, fácil de alterar e fácil de entender depois.

Antes de adicionar uma tecnologia, camada, abstração ou dependência, perguntar:

> **Isso resolve um problema que o BUSIVS BOT tem agora?**

Se a resposta for não, não adicionar.

### Evitar

- arquitetura mirabolante;
- abstrações prematuras;
- microserviços;
- frontend próprio sem necessidade;
- banco mais complexo que o necessário;
- classes, interfaces ou camadas criadas apenas por padrão arquitetural;
- dependências para problemas que algumas linhas de Python resolvem bem;
- otimização para uma escala que o projeto ainda não possui;
- implementar funcionalidades futuras antes do fluxo atual funcionar.

### Preferir

- Python simples e explícito;
- poucas dependências;
- funções pequenas;
- JSON para dados fixos;
- SQLite para o pouco estado persistente;
- uma única regra de negócio reutilizada por diferentes entradas, como `/local` e NFC;
- implementar uma funcionalidade, testar e só então seguir para a próxima;
- refatorar apenas quando a complexidade realmente aparecer.

**A arquitetura deve crescer somente quando o problema crescer.**

---

## Regra de infraestrutura e custo

> **O BUSIVS BOT deve buscar custo operacional zero ou próximo de zero.**

O projeto atende um ambiente universitário e não deve depender de infraestrutura cara para funcionar.

A hospedagem deve ser compatível com a natureza simples do sistema: um processo Python leve, conexão com o Telegram e armazenamento local pequeno.

### Estratégia por fase

#### Desenvolvimento

Rodar localmente no computador do desenvolvedor:

```text
Telegram
   ↓
Python local
   ↓
BUSIVS BOT
```

Usar `run_polling()` durante o desenvolvimento.

#### Protótipo / testes com alunos

Priorizar opções gratuitas ou de custo mínimo, desde que consigam manter o processo Python ativo.

Possibilidades a avaliar quando chegar a hora do deploy:

- serviço gratuito simples para protótipo;
- VM gratuita ou de baixíssimo custo;
- infraestrutura cedida pela própria UFRB, laboratório, grupo de pesquisa ou setor institucional.

#### Beta / produção

Critérios mínimos:

- executar Python 24/7;
- acesso à internet para comunicação com o Telegram;
- armazenamento persistente para o SQLite;
- custo zero ou muito baixo;
- configuração simples de manter.

Não escolher o provedor definitivo agora. Preços e planos mudam; a comparação deve ser feita no momento do deploy.

### Princípio de deploy

Enquanto não houver necessidade real, manter:

```text
Telegram
   ↓
bot.py
   ↓
SQLite
```

Evitar adicionar apenas para hospedagem:

- Nginx;
- Redis;
- filas;
- API Gateway;
- Kubernetes;
- banco gerenciado pago;
- frontend separado;
- microserviços.

Polling pode continuar sendo usado em produção se a hospedagem escolhida suportar um processo Python contínuo. Webhook só será adotado se trouxer uma vantagem concreta.

### Atenção ao SQLite

Ao escolher hospedagem, verificar se o filesystem é persistente. O arquivo do banco não pode desaparecer a cada reinicialização ou novo deploy.

---

## Visão do produto

O BUSIVS BOT será um bot de Telegram para estudantes da UFRB - Campus Cruz das Almas.

O bot deve responder três perguntas principais:

1. Qual é o próximo horário?
2. Onde o ônibus foi confirmado pela última vez?
3. Quando ele provavelmente chegará ao meu ponto?

## Escopo acordado

### Dados fixos

- pontos;
- ordem dos pontos;
- rotas;
- horários regulares;
- horários de férias;
- mensagens pré-definidas.

Esses dados devem ficar em JSON.

### Dados dinâmicos

- usuários autenticados;
- código de verificação de e-mail (temporário);
- última confirmação de passagem;
- histórico mínimo de confirmações;
- estado diário do Principal;
- estado diário do Micro;
- modo atual da rota.

SQLite é suficiente.

## Autenticação

O Telegram identifica o usuário pelo `telegram_id`.

Para ter permissão de confirmar passagem:

1. usuário informa e-mail institucional;
2. recebe código nesse e-mail;
3. confirma código no Telegram;
4. vínculo entre `telegram_id` e e-mail verificado é salvo.

Não criar senha própria e nunca solicitar senha institucional.

## Localização

Duas entradas, uma única regra de negócio:

- `/local` -> usuário escolhe ponto;
- NFC -> deep link abre ponto específico.

Ambas devem terminar na mesma função conceitual:

```python
registrar_passagem(
    veiculo,
    ponto_id,
    telegram_id,
    origem
)
```

`origem` pode ser `MANUAL` ou `NFC`.

## Principal e Micro

### Principal

Veículo regular. É esperado diariamente conforme horário oficial.

### Micro

Veículo de reforço e operação incerta.

Estados:

```text
NAO_CONFIRMADO
ATIVO
PROVAVELMENTE_INATIVO
ENCERRADO
```

O estado `PROVAVELMENTE_INATIVO` deve sempre ser apresentado como incerteza, nunca como confirmação de que o Micro não está operando.

## Rotas e portões

Percurso conceitual:

```text
GARAGEM
  ↓
VOLTA INTERNA
  ↓
PORTÃO 2 / TABELA
  ↓
VOLTA EXTERNA
  ↓
PORTÃO 1
  ↓
RETORNO INTERNO
  ↓
RU
```

Estados planejados:

```text
NORMAL
PORTAO_1_FECHADO
PORTAO_2_FECHADO
```

As rotas alternativas serão listas fixas em JSON. Não criar algoritmo de roteamento para percursos que já são conhecidos.

## Período de férias

Será um modo de calendário:

```text
LETIVO
FERIAS
```

Cada modo aponta para seu conjunto de horários.

## Avisos carinhosos

Planejados para pós-protótipo.

Exemplos:

- chuva;
- calor;
- alteração de rota;
- período de férias;
- mensagens curtas de bom dia.

---

# Estado atual do desenvolvimento

## Etapa 1 - Base do bot

**Concluída.**

Já implementado e validado localmente:

- configuração do token por `.env`;
- inicialização do `python-telegram-bot`;
- logging básico;
- comando `/start`;
- menu inicial com botões inline;
- execução local com `run_polling()`;
- correção dos handlers para usar `update.effective_message` quando necessário.

## Etapa 2 - Horários fixos do Principal

**Concluída para o ônibus Principal.**

Arquivos principais:

```text
src/
  bot.py
  config.py
  horarios.py

data/
  pontos.json
  rotas.json
  horarios_letivo.json
```

### Funcionalidades implementadas

- comando `/horarios`;
- comando `/listar_horarios`;
- botão `⏰ Próximos horários`;
- botão `📋 Listar horários`;
- seleção de período por botões:
  - 🌅 Manhã;
  - 🍽️ Almoço;
  - 🌤️ Tarde;
  - 🌙 Noite;
- mensagens de horário formatadas em HTML no Telegram;
- destaque visual de origem, sentido e previsão de retorno;
- cálculo do próximo horário com fuso UTC-3 usando apenas a biblioteca padrão;
- Micro permanece sem horários cadastrados nesta etapa.

### Regras dos períodos

As categorias são atalhos de consulta e podem se sobrepor.

```text
Manhã:   até 12:20
Almoço:  11:30 até 13:25
Tarde:   13:00 até antes de 17:30
Noite:   a partir de 17:30
```

A sobreposição de Almoço e Tarde é intencional para ajudar alunos que querem consultar especificamente o intervalo do RU.

### Origens reais das viagens

Os horários abaixo saem da **Garagem**:

```text
06:25
09:35
10:00
11:30
13:00
15:35
16:00
17:30
20:40
21:40
22:30
```

Os demais horários cadastrados do Principal usam **RU** como origem de serviço.

### Padrão visual adotado

Para RU:

```text
🍽️ 06:50  RU ➡️ RUA
   ↪️ Retorno Portão 1: 07:05–07:10
```

Para Garagem:

```text
🅿️ 06:25  Garagem ➡️ RUA
   ↪️ Retorno Portão 1: 06:40–06:45
```

Decisões visuais:

- manter 🍽️ para RU;
- usar 🅿️ para Garagem;
- usar `Portão 1` em vez de `Guarita Principal`;
- não exibir um bloco separado de `RETORNO / Origem / Sentido` no final da mensagem, porque isso pode confundir;
- mostrar a previsão de retorno junto de cada horário.

### Previsão até o Portão 1

A previsão é uma **estimativa**, não GPS.

#### Fluxo normal

Tempo estimado do RU até o Portão 1:

```text
15 a 20 minutos
```

Casos considerados normais incluem:

- 06:00 até 07:20;
- região de 09:40 / 10:00;
- 15:30 / 16:00;
- a partir das 20:00, podendo levar menos tempo.

#### Horário de pico

Tempo estimado:

```text
20 a 25 minutos
```

Faixas usadas atualmente:

```text
07:30 até 08:00
11:30 até 14:00
17:30 até 18:15
```

Nos horários de pico a interface deve informar que podem ocorrer atrasos.

#### Limitação atual

Para viagens cuja origem oficial é `Garagem`, a previsão do Portão 1 ainda é uma aproximação baseada no horário da viagem. Quando houver dados reais de passagem pelo RU, essa estimativa poderá ser refinada.

---

# Próxima etapa - Pontos, rota, sentido e próximo ponto

`data/pontos.json` e `data/rotas.json` ainda estão vazios. A próxima etapa deve preenchê-los apenas com a rota validada pelo usuário.

## Objetivo

Permitir que o bot responda algo como:

```text
📍 Último registro: Ponto Externo 2 (Canãa)
🕐 Há 2 min

⬅️ Sentido: RU
➡️ Próximo ponto: Portão 1
```

ou:

```text
📍 Último registro: Pavilhão de Aulas I
➡️ Sentido: Rua
➡️ Próximo ponto: Biblioteca
```

## Regra para descobrir o sentido

Não inferir o sentido apenas pelo nome do ponto, porque alguns pontos podem aparecer em mais de um trecho da rota.

Usar pelo menos:

```text
ponto anterior
ponto atual
```

Exemplos acordados:

```text
Pavilhão de Aulas I → Biblioteca
= sentido Rua
```

```text
Portão 1 → Biblioteca
= sentido RU
```

```text
Ponto Externo 2 / Canãa → Portão 1
= sentido RU
```

Com a sequência fixa da rota será possível determinar:

1. último ponto confirmado;
2. sentido atual (`Rua` ou `RU`);
3. próximo ponto esperado;
4. posteriormente, ETA aproximado para o próximo ponto.

## Princípio técnico para a rota

Não criar algoritmo de roteamento.

A solução deve ser uma sequência fixa e validada de pontos em JSON, com lógica simples de posição anterior/atual/próxima.

Exemplo conceitual:

```text
ponto anterior + ponto atual
        ↓
identificar trecho da rota
        ↓
sentido atual
        ↓
próximo ponto
```

Isso mantém o sistema simples e também resolve ambiguidades de pontos repetidos, como Biblioteca.

## Ordem imediata sugerida

1. receber do usuário a ordem real dos pontos do percurso completo;
2. preencher `pontos.json`;
3. preencher `rotas.json`;
4. criar função simples para descobrir sentido e próximo ponto;
5. criar uma simulação manual antes de persistir confirmações;
6. depois conectar essa regra ao futuro fluxo `/local`.

**Ainda não implementar NFC.** Primeiro validar o fluxo manual e a lógica de rota.

---

## Estado resumido

```text
Etapa 1 - Base do bot                         ✅ concluída
Etapa 2 - Horários fixos do Principal        ✅ concluída
Etapa 3 - Pontos / rota / sentido             ⏭️ próxima
Etapa 4 - Autenticação institucional          ⏳ futura
Etapa 5 - Informar passagem (/local)           ⏳ futura
Etapa 6 - ETA por confirmações                 ⏳ futura
Etapa 7 - NFC                                  ⏳ futura
```
