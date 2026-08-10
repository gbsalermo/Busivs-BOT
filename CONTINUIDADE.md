# CONTINUIDADE - BUSIVS BOT

Documento de retomada rápida do projeto.

## Princípio principal

> **O BUSIVS BOT deve ser simples, eficaz e de custo zero ou próximo de zero.**

O projeto é desenvolvido principalmente por vibecoding, mas toda implementação deve continuar pequena, legível, testável e compreensível.

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

SQLite continua sendo uma opção futura caso persistência passe a ser necessária.

---

# Visão do produto

O BUSIVS BOT é um bot de Telegram para estudantes da UFRB - Campus Cruz das Almas.

O objetivo é responder principalmente:

1. Qual é o próximo horário do circular?
2. Onde o ônibus foi confirmado pela última vez?
3. Qual o sentido e o próximo ponto esperado?
4. Existe indício de atraso?

O sistema deve sempre diferenciar:

- **confirmação real feita por usuário**;
- **estimativa baseada em horário oficial**;
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

---

# Ônibus

## Principal

Ônibus regular, com horários fixos.

## Micro

Ônibus de reforço e operação incerta. Ainda não implementado.

Estados futuros possíveis:

```text
NAO_CONFIRMADO
ATIVO
PROVAVELMENTE_INATIVO
ENCERRADO
```

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
- diferenciação visual entre RU e Garagem.

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

Estimativa geral RU → Portão 1:

```text
normal: 15 a 20 min
pico:   20 a 25 min
```

A previsão é estimativa, não GPS.

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

**Implementada durante a validação da Etapa 3.**

Fluxo atual:

- usuário toca em `📍 Informar passagem`;
- escolhe o ponto por botão, sem precisar digitar;
- o estado é atualizado em memória;
- primeira confirmação consecutiva do mesmo ponto é a que vale.

Experiência do usuário:

```text
Primeira resposta válida:
Valeu! Registramos o ponto 😊

Resposta repetida do mesmo ponto:
Obrigado pela informação 😊
```

O segundo usuário não é informado de que sua resposta foi descartada, para não desmotivar a colaboração.

Estado atual fica em memória e é apagado quando o processo do bot reinicia. Isso é aceitável no protótipo porque a informação é pequena e altamente temporária.

---

# Etapa 5 - Onde está / última confirmação / estimativas

**Etapa atual.**

Branch:

```text
feat/localizacao-etapa5
```

Já implementado:

- última confirmação real;
- horário exato da confirmação;
- tempo decorrido, como `há 3 min`;
- sentido atual;
- próximo ponto esperado;
- uso do horário oficial da Garagem como contexto quando existe apenas uma confirmação;
- linguagem de incerteza: `deve ter saído`, `sentido provável`, nunca confirmação sem dado real.

Exemplo:

```text
📍 Última confirmação: Biblioteca
🕐 há 3 min (10:16:20)
➡️ Sentido: RUA
⏭️ Próximo: Pavilhão de Aulas II
```

## Regra experimental de possível atraso - Portão 1

Por enquanto o mecanismo de atraso será estudado **somente para o Portão 1**.

Primeira regra implementada:

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
📍 O último registro ainda está em Biblioteca / Pavilhão II.
ℹ️ É uma estimativa, não uma confirmação de atraso.
```

Não disparar essa regra para a Biblioteca no retorno, quando o sentido já for RU.

Essa regra é experimental e deve ser validada antes de expandir para outros horários ou pontos.

---

# Pós-protótipo - alertas de atraso

Estudar a possibilidade de o bot enviar **alertas automáticos de possível atraso** para usuários que estejam com o chat ativo ou que optem por receber esse tipo de aviso.

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

Exemplo futuro:

```text
⚠️ O circular pode chegar com atraso ao Portão 1.
Última confirmação: Biblioteca, há 2 min.
```

Esse recurso fica **pós-protótipo** porque envolve decidir:

- quem deve receber o alerta;
- como o usuário ativa/desativa notificações;
- frequência máxima para evitar spam;
- quando um possível atraso é relevante o suficiente para gerar notificação.

Não implementar notificações automáticas antes de validar bem a lógica de atraso no uso real.

---

# Próximas etapas

```text
Etapa 1  - Base do bot                              ✅
Etapa 2  - Horários fixos do Principal             ✅
Etapa 3  - Pontos / rota / sentido / próximo ponto ✅
Etapa 4  - Informar passagem                       ✅ protótipo
Etapa 5  - Localização / tempo / atraso             ⏭️ atual
Etapa 6  - Principal + Micro                        ⏳
Etapa 7  - NFC                                      ⏳
Etapa 8  - Desvios dos portões                      ⏳
Etapa 9  - Modo de férias                           ⏳
Etapa 10 - Autenticação institucional               ⏳ pós-protótipo / se necessária
Etapa 11 - Avisos e alertas automáticos             ⏳ pós-protótipo
```

## Próximo passo imediato

Testar a Etapa 5 com cenários controlados antes de levar para `main`:

1. confirmar um ponto e verificar `há X min`;
2. validar sentido e próximo ponto;
3. simular/validar Biblioteca ou Pavilhão II entre 10:15 e 10:20;
4. verificar se aparece `⚠️ Possível atraso no Portão 1`;
5. confirmar que Biblioteca no sentido RU não gera falso alerta.
