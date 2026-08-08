# CONTINUIDADE - BUSIVS BOT

Documento de retomada rápida do projeto.

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

Não criar senha própria.

## Localização

Duas entradas, uma única regra de negócio:

- `/local` -> usuário escolhe ponto;
- NFC -> deep link abre ponto específico.

Ambas chamam a mesma função conceitual:

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

O estado `PROVAVELMENTE_INATIVO` deve ser apresentado como incerteza.

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

As rotas alternativas serão listas fixas em JSON.

## Período de férias

Será um modo de calendário:

```text
LETIVO
FERIAS
```

Cada modo aponta para um arquivo de horários.

## Avisos carinhosos

Planejados para pós-protótipo.

Exemplos:

- chuva;
- calor;
- alteração de rota;
- período de férias;
- mensagens curtas de bom dia.

## Próximo passo técnico

Criar a base Python com:

```text
src/
  bot.py
  config.py
  db.py
  services/
    auth.py
    localizacao.py
    previsao.py
    horarios.py
```

Primeiro objetivo executável:

1. bot responde `/start`;
2. bot carrega pontos e horários de JSON;
3. `/horarios`;
4. `/local`;
5. salvar confirmação;
6. `/onde` mostra última confirmação.

Não implementar NFC antes do fluxo manual estar funcionando.
