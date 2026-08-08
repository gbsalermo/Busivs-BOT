# Arquitetura

## Princípio

O BUSIVS BOT não é um sistema de rastreamento GPS. Ele mantém uma estimativa comunitária baseada em passagens confirmadas.

## Componentes

```text
Telegram
    |
    v
bot.py
    |
    +--------------------+
    |                    |
    v                    v
services/             data/*.json
    |                 pontos
    |                 rotas
    |                 horários
    |                 mensagens
    v
SQLite
usuários
confirmações
estado diário
```

## Fonte estática x estado dinâmico

### JSON

```text
pontos.json
rotas.json
horarios_letivo.json
horarios_ferias.json
mensagens.json
```

### SQLite

```text
usuarios
confirmacoes
estado_veiculo
configuracao_runtime
```

## Entidades mínimas

### Usuario

```text
telegram_id
email
verificado_em
```

### Confirmacao

```text
id
telegram_id
veiculo
ponto_id
origem
confirmado_em
```

### EstadoVeiculo

```text
veiculo
status
ultimo_ponto
ultima_confirmacao
```

## Previsão

Entrada:

```text
veículo
último ponto confirmado
hora da confirmação
rota ativa
tempos entre os próximos pontos
```

Saída:

```text
ETA Ponto N+1
ETA Ponto N+2
...
```

Cada nova confirmação substitui a referência anterior.

## Segurança mínima

- confirmar passagem exige e-mail institucional validado;
- código de e-mail expira;
- rate limit de confirmações;
- não armazenar senha institucional;
- não solicitar credenciais da UFRB;
- Telegram ID não deve aparecer publicamente;
- histórico pode ser minimizado/expirado.

## Regras anti-erro

No protótipo não é necessário criar um sistema antifraude complexo.

Validar apenas:

- autenticação;
- intervalo mínimo entre confirmações do mesmo usuário;
- ponto existe;
- veículo existe;
- sequência temporal plausível;
- registro muito antigo não pode sobrescrever um mais novo.

## Estrutura prevista quando iniciar o código

```text
Busivs-BOT/
├── src/
│   ├── bot.py
│   ├── config.py
│   ├── db.py
│   └── services/
│       ├── auth.py
│       ├── horarios.py
│       ├── localizacao.py
│       └── previsao.py
├── data/
│   ├── pontos.json
│   ├── rotas.json
│   ├── horarios_letivo.json
│   ├── horarios_ferias.json
│   └── mensagens.json
├── docs/
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```
