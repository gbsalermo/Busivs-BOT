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
PORTÃO 1 / PRINCIPAL
  ↓
RETORNO INTERNO
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

## Estado atual do desenvolvimento

Branch de trabalho:

```text
feat/python-base
```

Base Python criada com:

```text
src/
  bot.py
  config.py

data/
  pontos.json
  rotas.json
  horarios_letivo.json

.env.example
requirements.txt
```

Já implementado:

- configuração do token por `.env`;
- inicialização do `python-telegram-bot`;
- logging básico;
- comando `/start`;
- menu inicial com botões inline;
- arquivos JSON preparados para receber os dados oficiais.

Os botões do menu ainda não executam ações. Isso é intencional nesta etapa.

## Próximo passo técnico

Primeiro validar localmente que:

1. ambiente virtual é criado;
2. dependências instalam;
3. token é carregado pelo `.env`;
4. bot inicia;
5. `/start` mostra o menu corretamente.

Depois disso, implementar **uma funcionalidade por vez**.

Próxima funcionalidade planejada:

```text
⏰ Próximos horários
```

Ordem imediata sugerida:

1. validar os horários oficiais;
2. preencher `horarios_letivo.json`;
3. criar leitura simples do JSON;
4. calcular próximo horário;
5. ligar o botão `Próximos horários`;
6. testar no Telegram.

Só depois seguir para `/local`, persistência das confirmações, previsão e NFC.

**Não implementar NFC antes do fluxo manual estar funcionando.**
