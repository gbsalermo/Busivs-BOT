# BUSIVS BOT 🚌

Bot comunitário para auxiliar estudantes da **UFRB - Campus Cruz das Almas** a consultar horários do circular e acompanhar sua posição de forma colaborativa.

> **Status atual:** protótipo funcional, rodando via Telegram e já validado em testes manuais de rota, localização, retorno e proteção contra registros fora de circulação.

---

## O problema

Quem utiliza o circular nem sempre precisa de GPS em tempo real. Muitas vezes as perguntas são mais simples:

- Qual é a próxima saída?
- Tem uma volta acontecendo agora?
- Onde o ônibus foi visto por último?
- Para qual lado ele está indo?
- Qual é o próximo ponto?
- Ele ainda está circulando ou provavelmente já voltou para a Garagem?

O BUSIVS BOT tenta responder isso usando duas fontes simples:

1. **horários oficiais cadastrados**;
2. **confirmações colaborativas de passagem feitas pelos alunos**.

A proposta é manter o sistema pequeno, gratuito e fácil de continuar por outros estudantes.

---

## Interface

O Telegram é toda a interface do protótipo. Não existe frontend separado.

![Interface inicial do BUSIVS BOT](docs/images/interface-inicial.png)

Menu atual:

```text
🚌 Onde está o ônibus?
📍 Informar passagem
⏰ Próximos horários
📋 Listar horários
🗺️ Rota atual
📢 Avisos
```

---

# O que já funciona

## ⏰ Horários do circular Principal

O bot consulta os horários cadastrados em JSON e consegue mostrar:

- próxima viagem;
- viagem seguinte;
- horários por período;
- origem da saída;
- previsão aproximada de retorno pelo Portão 1;
- viagem possivelmente em andamento;
- percurso de retorno;
- período em que o ônibus provavelmente aguarda a próxima saída.

Exemplo:

```text
🚌 VOLTA POSSIVELMENTE EM ANDAMENTO
🅿️ 10:00  Garagem ➡️ RUA
   ↪️ Retorno Portão 1: 10:15–10:20

🟢 PRÓXIMA VIAGEM
🅿️ 11:30  Garagem ➡️ RUA
```

---

## 📍 Confirmação colaborativa de passagem

O aluno toca em **Informar passagem** e escolhe o ponto por botão.

Não é necessário digitar o nome do local.

Resposta para um registro válido:

```text
Valeu! Registramos o ponto 😊
```

Se outra pessoa registrar imediatamente o mesmo ponto:

```text
Obrigado pela informação 😊
```

O segundo registro não altera novamente o estado, mas também não informa ao usuário que sua contribuição foi descartada.

---

## 🚌 Onde está o ônibus?

O comportamento depende do nível de informação disponível.

### Sem confirmação real, mas com viagem prevista

```text
🚌 Pelo horário oficial, o ônibus deve ter saído da Garagem às 10:00.
➡️ Sentido provável: RUA

ℹ️ Informação baseada apenas no horário previsto, não em confirmação real.
```

A linguagem é propositalmente incerta: horário previsto nunca é tratado como GPS ou confirmação de saída.

### Com confirmação colaborativa

```text
📍 Última confirmação: Ponto Externo I / Alex
🕐 agora mesmo (10:20:49)

⏭️ Próximo:
     📍 Ponto Externo II / Canãa
➡️ Sentido: RUA
```

O bot usa o contexto da rota para descobrir sentido e próximo ponto.

---

## ↩️ Percurso de retorno

Depois da janela estimada de passagem pelo Portão 1, o sistema pode identificar que a viagem provavelmente entrou no percurso de retorno.

```text
↩️ Percurso de retorno
🚌 Pelo horário, o ônibus provavelmente está no percurso de retorno.
⬅️ Sentido: Garagem
📍 O ônibus ainda segue atendendo pontos durante esse percurso.
```

Isso evita a interpretação errada de que "retornar para a Garagem" significa deixar de atender os pontos da volta.

---

## 🅿️ Provavelmente aguardando na origem

Quando a janela estimada de retorno termina e ainda falta tempo para a próxima saída:

```text
🅿️ Provavelmente na Garagem
🚌 Pelo horário, o ônibus provavelmente já concluiu o percurso anterior.

⏰ Próxima saída prevista:
     🕐 11:30 — Garagem
```

No protótipo atual, para uma saída normal às 10:00, o ciclo aproximado fica:

```text
10:00–10:20 → viagem possivelmente em andamento
10:25–10:40 → percurso de retorno
10:40–11:30 → provavelmente na Garagem
11:30       → próxima saída
```

Esses tempos são aproximações e podem ser refinados com dados reais futuramente.

---

## 🛡️ Proteção contra registros fora de circulação

O bot possui uma primeira camada simples contra alguém informar uma passagem quando provavelmente não existe viagem ativa.

Regra:

```text
aguardando próxima saída
+
sem confirmação válida nos últimos 30 minutos
=
bloquear nova passagem
```

Exemplo:

```text
🚫 Não há percurso ativo no momento.

🚌 Pelo horário, o ônibus provavelmente está em Garagem.
⏰ Próxima saída prevista:
     🕐 11:30 — Garagem
```

A margem de 30 minutos é importante para não bloquear um ônibus que esteja realmente atrasado.

---

## ⚠️ Possível atraso

Existe uma primeira regra experimental de atraso para o **Portão 1**.

Se entre aproximadamente `10:15` e `10:20` a última confirmação ainda estiver em **Biblioteca** ou **Pavilhão II**, no sentido da Rua, o bot pode indicar:

```text
⚠️ Possível atraso no Portão 1
🚪 Passagem esperada por volta de 10:20.
ℹ️ É uma estimativa, não uma confirmação de atraso.
```

Essa lógica ainda não foi generalizada para todos os horários.

---

# Rota cadastrada

```text
RU / Residências
↓
Fitotecnia
↓
Prédio de Solos / NEAS / Eng. Florestal
↓
Pavilhão de Aulas I
↓
Biblioteca
↓
Pavilhão de Aulas II
↓
Pavilhão de Engenharia (opcional)
↓
Portão 2 / Tabela
↓
Ponto Externo I / Alex
↓
Ponto Externo II / Canãa
↓
Portão 1
↓
Biblioteca
↓
Torre / COTEC (opcional)
↓
RU / Residências
```

### Por que a rota precisa de contexto?

A **Biblioteca aparece duas vezes** no trajeto.

Por isso o sistema não pode fazer algo simplista como:

```python
if ponto == "biblioteca":
    sentido = "RUA"
```

Ele considera registros anteriores para distinguir, por exemplo:

```text
Pavilhão I → Biblioteca = sentido RUA
Portão 1 → Biblioteca   = sentido RU
```

Pontos opcionais também podem ser pulados sem quebrar o fluxo.

---

# Arquitetura atual

A arquitetura propositalmente é pequena:

```text
┌─────────────────────┐
│      Telegram       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│       bot.py        │  comandos, callbacks e interface
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌──────────┐ ┌────────────┐
│horarios.py│ │passagens.py│
└────┬─────┘ └──────┬─────┘
     │              │
     │              ▼
     │        ┌──────────┐
     │        │ rota.py  │
     │        └────┬─────┘
     │             │
     ▼             ▼
┌────────────────────────┐
│       arquivos JSON    │
│ horários / rota / pontos│
└────────────────────────┘
```

Não existem atualmente:

- servidor web;
- frontend próprio;
- PostgreSQL;
- Redis;
- microserviços;
- autenticação obrigatória;
- serviço de GPS.

Isso é intencional.

---

# Stack atual

- Python
- `python-telegram-bot`
- `python-dotenv`
- JSON
- estado temporário em memória
- Telegram Bot API

### Possíveis tecnologias futuras

Somente se aparecer necessidade concreta:

- SQLite para persistência;
- NFC para confirmação de pontos;
- autenticação institucional;
- mecanismo de avisos automáticos.

---

# Estrutura importante do projeto

Para quem está chegando agora, estes são os arquivos principais:

```text
Busivs-BOT/
├── data/
│   ├── horarios_letivo.json   # horários oficiais
│   ├── pontos.json            # pontos e aliases
│   └── rotas.json             # sequência da rota
│
├── src/
│   ├── bot.py                 # Telegram: menus, comandos e callbacks
│   ├── horarios.py            # regras de horário e estados da viagem
│   ├── passagens.py           # confirmações, localização e proteção
│   ├── rota.py                # análise da rota, sentido e próximo ponto
│   └── config.py              # configuração / token
│
├── tests/
│   ├── test_rota.py           # testes automáticos de rota
│   └── simular_rota.py        # simulador manual
│
├── docs/                      # documentação complementar
├── CONTINUIDADE.md            # estado atual e próximos passos
├── requirements.txt
└── README.md
```

---

# Onde mexer?

### Quero alterar um horário

Edite:

```text
data/horarios_letivo.json
```

Evite escrever horários diretamente dentro do Python.

### Quero adicionar ou renomear um ponto

Edite:

```text
data/pontos.json
```

Depois verifique se a rota ainda referencia o ID correto.

### Quero mudar a sequência da rota

Edite:

```text
data/rotas.json
```

Depois rode os testes de rota.

### Quero mudar cálculo de horário, Portão 1 ou estado da viagem

Arquivo:

```text
src/horarios.py
```

### Quero mudar registro colaborativo ou "Onde está o ônibus?"

Arquivo:

```text
src/passagens.py
```

### Quero mudar botões, comandos ou textos do Telegram

Arquivo:

```text
src/bot.py
```

### Quero mudar a interpretação de sentido / próximo ponto

Arquivo:

```text
src/rota.py
```

---

# Como executar localmente

## 1. Clone o projeto

```bash
git clone https://github.com/gbsalermo/Busivs-BOT.git
cd Busivs-BOT
```

## 2. Crie um ambiente virtual

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

## 3. Instale as dependências

```bash
pip install -r requirements.txt
```

## 4. Configure o token

Crie um arquivo `.env` na raiz:

```env
TELEGRAM_BOT_TOKEN=seu_token_aqui
```

> Nunca envie o token para o GitHub.

## 5. Execute

```bash
python src/bot.py
```

---

# Testes

## Testes automáticos da rota

```bash
python -m unittest tests/test_rota.py
```

Os cenários incluem:

- Biblioteca na ida;
- Biblioteca no retorno;
- Canãa → Portão 1;
- parada opcional utilizada;
- parada opcional pulada;
- transições inválidas.

## Simulador manual

```bash
python tests/simular_rota.py
```

Útil para entender a sequência do circular sem precisar ficar clicando no Telegram.

---

# Regras importantes para contribuir

1. **Não tratar estimativa como confirmação.**
2. **Não inferir sentido apenas pelo nome do ponto.**
3. **Manter horários e rotas nos JSONs sempre que possível.**
4. **Evitar adicionar infraestrutura sem necessidade concreta.**
5. **Testar Biblioteca nos dois sentidos ao alterar lógica de rota.**
6. **Considerar que ônibus pode estar atrasado antes de bloquear uma passagem.**
7. **Preferir uma solução simples que outro aluno consiga entender.**

---

# Estado atual do roadmap

```text
Etapa 1  - Base do bot                              ✅
Etapa 2  - Horários fixos do Principal             ✅
Etapa 3  - Pontos / rota / sentido / próximo ponto ✅
Etapa 4  - Informar passagem                       ✅ protótipo
Etapa 5  - Localização / tempo / estados / proteção ✅ protótipo validado
Etapa 6  - Principal + Micro                        ⏭️ próxima
Etapa 7  - NFC                                      ⏳
Etapa 8  - Desvios dos portões                      ⏳
Etapa 9  - Modo de férias                           ⏳
Etapa 10 - Autenticação institucional               ⏳ se necessária
Etapa 11 - Avisos e alertas automáticos             ⏳ pós-protótipo
```

---

# Próximas ideias

### Micro-ônibus

Adicionar o veículo de reforço sem quebrar o fluxo simples do Principal.

### NFC

Tags nos pontos poderão abrir o Telegram com um deep link associado ao ponto, tornando a confirmação mais confiável e rápida.

### Persistência

O estado atual fica apenas em memória. SQLite pode ser considerado quando houver necessidade de:

- sobreviver a reinícios;
- guardar histórico;
- calcular tempos reais de percurso;
- melhorar estimativas com dados coletados.

### Alertas

No pós-protótipo, estudar alertas opt-in de possível atraso para usuários interessados.

---

# Documentação

- [Continuidade e estado atual](CONTINUIDADE.md)
- [Fluxo do Telegram](docs/FLUXO_TELEGRAM.md)
- [Roadmap até Beta](docs/ROADMAP_BETA.md)
- [Arquitetura](docs/ARQUITETURA.md)

---

## Ideia central

O BUSIVS BOT não tenta começar como um sistema complexo de rastreamento.

Ele parte de uma pergunta mais prática:

> **Com os horários que já existem e a colaboração dos próprios alunos, qual é a informação mais útil que conseguimos entregar agora?**

A arquitetura deve crescer somente quando essa resposta exigir.