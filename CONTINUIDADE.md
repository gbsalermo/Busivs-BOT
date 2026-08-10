# CONTINUIDADE - BUSIVS BOT

Documento de retomada rápida do projeto.

## Princípio principal

> **O BUSIVS BOT deve ser simples, eficaz e de custo zero ou próximo de zero.**

O projeto é desenvolvido de forma incremental. Toda implementação deve continuar pequena, legível, testável e compreensível.

Antes de adicionar tecnologia, camada ou dependência, perguntar:

> **Isso resolve um problema que o BUSIVS BOT tem agora?**

Evitar overengineering, microserviços, frontend próprio, Redis, Kubernetes, banco gerenciado e outras estruturas que não sejam necessárias para o estágio atual.

Stack atual:

```text
Telegram
   ↓
Python + python-telegram-bot
   ↓
JSON para dados fixos
   ↓
Estado temporário em memória
```

Dependências atuais:

```text
python-telegram-bot
python-dotenv
```

SQLite continua sendo apenas uma opção futura caso persistência passe a ser necessária.

---

# Visão do produto

O BUSIVS BOT é um bot de Telegram para estudantes da UFRB - Campus Cruz das Almas.

O objetivo é responder principalmente:

1. Qual é o próximo horário do circular?
2. Existe uma viagem provavelmente acontecendo agora?
3. Onde o ônibus foi confirmado pela última vez?
4. Qual o sentido e o próximo ponto esperado?
5. O ônibus provavelmente está no retorno ou aguardando a próxima saída?
6. Existe algum indício de atraso?

O sistema deve sempre diferenciar:

- **confirmação real feita por usuário**;
- **estimativa baseada no horário oficial**;
- **inferência de possível atraso**.

Nunca apresentar estimativa como certeza.

---

# Autenticação

A autenticação institucional foi adiada para o pós-protótipo.

Motivo: horários e localização do circular são informações públicas, e exigir autenticação aumentaria o atrito para o aluno.

No protótipo:

- consulta é pública;
- informar passagem é público;
- `telegram_id` pode ser mantido internamente para controles simples;
- autenticação por e-mail institucional só será estudada se surgir problema real de abuso ou confiança.

A primeira proteção contra abuso já foi implementada usando **contexto de horário + confirmação recente**, sem exigir login.

---

# Ônibus

## Principal

Ônibus regular, com horários fixos. É o veículo implementado atualmente.

## Micro

Ônibus de reforço e operação incerta. Ainda não implementado.

---

# Etapa 1 - Base do bot

**Concluída.**

Implementado:

- `.env` para token;
- `python-telegram-bot`;
- `/start`;
- menu com botões inline;
- logging;
- `run_polling()`;
- botão de voltar ao menu.

---

# Etapa 2 - Horários fixos

**Concluída para o Principal.**

Implementado:

- `/horarios`;
- `/listar_horarios`;
- próximos horários;
- períodos Manhã / Almoço / Tarde / Noite;
- origem da viagem;
- estimativa de retorno pelo Portão 1;
- diferenciação visual entre RU e Garagem;
- identificação de viagem possivelmente em andamento;
- identificação de percurso de retorno;
- identificação de período aguardando a próxima saída.

Horários cuja origem é **Garagem**:

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

Demais horários cadastrados usam RU como origem.

Estimativa geral até o Portão 1:

```text
normal: 15 a 20 min
pico:   20 a 25 min
```

A previsão é estimativa, não GPS.

## Estados baseados em horário

O protótipo passou a trabalhar com uma sequência simples de estados:

```text
1. viagem possivelmente em andamento
2. percurso de retorno
3. provavelmente aguardando na origem
4. próxima saída prevista
```

Exemplo para a saída de 10:00:

```text
10:00–10:20 → viagem possivelmente em andamento
10:25–10:40 → percurso de retorno
10:40–11:30 → provavelmente na Garagem
11:30       → próxima saída
```

As janelas são aproximações e podem ser refinadas depois com dados reais de uso.

---

# Etapa 3 - Pontos, rota, sentido e próximo ponto

**Concluída e validada.**

Rota cadastrada:

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

A direção é inferida usando contexto de rota, principalmente `ponto anterior + ponto atual`, porque Biblioteca aparece em dois momentos diferentes.

Exemplos:

```text
Pavilhão I → Biblioteca = sentido RUA
Portão 1 → Biblioteca = sentido RU
Canãa → Portão 1 = sentido RU
```

Pontos opcionais podem ser pulados sem quebrar a análise.

---

# Etapa 4 - Informar passagem

**Concluída no protótipo.**

Fluxo atual:

- usuário toca em `📍 Informar passagem`;
- escolhe o ponto por botão, sem precisar digitar;
- o estado é atualizado em memória;
- registros consecutivos do mesmo ponto não alteram novamente o estado.

Experiência do usuário:

```text
Primeira resposta válida:
Valeu! Registramos o ponto 😊

Resposta repetida do mesmo ponto:
Obrigado pela informação 😊
```

O segundo usuário não é informado de que sua resposta foi descartada, para não desmotivar a colaboração.

Estado atual fica em memória e é apagado quando o processo do bot reinicia. Isso continua aceitável no protótipo porque a informação é pequena e altamente temporária.

## Proteção contra passagem falsa fora de circulação

**Implementada e testada com sucesso.**

Regra atual:

```text
ônibus em estado de aguardar próxima saída
+
sem confirmação válida nos últimos 30 minutos
=
bloquear nova passagem
```

Objetivo: impedir que alguém registre uma passagem quando o horário indica que o ônibus provavelmente já está parado na origem.

A margem de 30 minutos existe para não bloquear um ônibus que esteja realmente atrasado.

Exemplo de resposta:

```text
🚫 Não há percurso ativo no momento.

🚌 Pelo horário, o ônibus provavelmente está em Garagem.
⏰ Próxima saída prevista:
     🕐 11:30 — Garagem
```

---

# Etapa 5 - Onde está / última confirmação / estimativas

**Concluída no protótipo inicial e validada manualmente.**

A implementação já está na `main`.

## Sem confirmação real

Se existir uma viagem compatível com o horário oficial, o bot informa uma estimativa de saída sem afirmar que ela realmente aconteceu.

Exemplo:

```text
🚌 Pelo horário oficial, o ônibus deve ter saído da Garagem às 10:00.
➡️ Sentido provável: RUA

ℹ️ Informação baseada apenas no horário previsto, não em confirmação real.
```

## Primeira confirmação

A primeira confirmação usa o horário oficial como contexto para estimar sentido e próximo ponto.

## Duas ou mais confirmações

Depois que existe contexto suficiente de rota, a apresentação mostra apenas o que é útil para o aluno:

```text
📍 Última confirmação: Ponto Externo I / Alex
🕐 agora mesmo (10:20:49)

⏭️ Próximo:
     📍 Ponto Externo II / Canãa
➡️ Sentido: RUA
```

Não existe mais a ideia de mostrar um segundo campo de "último ponto" ou "ponto de referência da rota".

## Percurso de retorno

Depois da janela estimada do Portão 1, o bot pode informar:

```text
↩️ Percurso de retorno
🚌 Pelo horário, o ônibus provavelmente está no percurso de retorno.
⬅️ Sentido: Garagem
📍 O ônibus ainda segue atendendo pontos durante esse percurso.
```

A mensagem evita dar a impressão de que o ônibus deixa de atender pontos assim que entra no retorno.

## Aguardando próxima saída

Depois da janela estimada de retorno:

```text
🅿️ Provavelmente na Garagem
🚌 Pelo horário, o ônibus provavelmente já concluiu o percurso anterior.

⏰ Próxima saída prevista:
     🕐 11:30 — Garagem
```

Esse estado também é usado pela proteção contra registros falsos.

## Tempo desde a confirmação

A confirmação apresenta tempo decorrido:

```text
agora mesmo
há 4 min
há 1h 12min
```

O horário exato continua aparecendo entre parênteses durante o protótipo para facilitar testes.

## Regra experimental de possível atraso - Portão 1

Por enquanto o mecanismo de atraso continua restrito ao primeiro caso estudado.

Regra:

```text
janela: 10:15 até 10:20
último ponto: Biblioteca ou Pavilhão II
contexto: sentido RUA
previsão Portão 1: por volta de 10:20
```

Nesse caso o bot pode mostrar:

```text
⚠️ Possível atraso no Portão 1
🚪 Passagem esperada por volta de 10:20.
ℹ️ É uma estimativa, não uma confirmação de atraso.
```

Não disparar essa regra para Biblioteca no retorno, quando o sentido já for RU.

Essa regra continua experimental. Não generalizar para todos os horários antes de observar o uso real.

---

# Testes já realizados

## Rota

A suíte de rota cobre cenários como:

- Biblioteca na ida;
- Biblioteca no retorno;
- Canãa → Portão 1;
- pontos opcionais atendidos ou pulados;
- transição inválida;
- ponto inexistente.

Os testes da rota já passaram com sucesso.

## Testes manuais da Etapa 5

Foram validados manualmente:

- confirmação de passagem;
- tempo decorrido;
- sentido e próximo ponto;
- estado de viagem por horário;
- percurso de retorno;
- estado de provável espera na Garagem;
- próxima saída prevista;
- bloqueio de passagem fora de circulação sem confirmação recente.

---

# Pós-protótipo - alertas de atraso

Estudar a possibilidade de o bot enviar **alertas automáticos de possível atraso** para usuários que optem por receber esse tipo de aviso.

Ideia conceitual:

```text
confirmação colaborativa
        ↓
comparação com horário esperado
        ↓
risco de atraso detectado
        ↓
alerta para usuários interessados
```

Esse recurso fica pós-protótipo porque envolve decidir:

- quem recebe;
- opt-in / opt-out;
- frequência máxima;
- limite de confiança para gerar alerta;
- prevenção de spam.

---

# Próximas etapas

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
Etapa 10 - Autenticação institucional               ⏳ pós-protótipo / se necessária
Etapa 11 - Avisos e alertas automáticos             ⏳ pós-protótipo
```

---

# Pontos de atenção antes de evoluir

- estado dinâmico ainda é perdido quando o bot reinicia;
- não há histórico de passagens;
- não há banco de dados;
- não há autenticação institucional;
- Micro ainda não foi implementado;
- tempos de retorno são aproximações do protótipo;
- confirmações reais devem continuar tendo prioridade sobre estimativas de horário;
- Biblioteca aparece duas vezes na rota, então nunca inferir direção apenas pelo nome do ponto;
- NFC deverá futuramente se tornar uma fonte de confirmação mais confiável que o clique manual.

## Próximo passo recomendado

Começar a **Etapa 6 - Principal + Micro**, sem adicionar infraestrutura nova antes de existir uma necessidade concreta.