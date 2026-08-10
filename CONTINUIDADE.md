# CONTINUIDADE - BUSIVS BOT

Documento técnico de retomada rápida do projeto.

---

# Regras importantes para contribuir

Antes de mexer no projeto:

1. **Não tratar estimativa como confirmação.**
2. **Não inferir sentido apenas pelo nome do ponto.**
3. **Manter horários, pontos e rotas nos JSONs sempre que possível.**
4. **Evitar infraestrutura sem necessidade concreta.**
5. **Testar Biblioteca nos dois sentidos ao alterar a lógica de rota.**
6. **Considerar atraso real antes de bloquear uma passagem.**
7. **Preferir soluções pequenas e compreensíveis por outros alunos.**
8. **Não adicionar serviços, banco ou dependências sem um problema atual que justifique.**
9. **Preservar sempre a diferença entre dado confirmado e dado estimado.**
10. **Dados de localização são temporários: o objetivo é representar o ônibus agora, não criar histórico permanente por padrão.**
11. **Viagens consecutivas do mesmo bloco operacional podem compartilhar contexto; uma nova saída não significa automaticamente apagar o estado.**

## Princípio principal

> **O BUSIVS BOT deve ser simples, eficaz e de custo zero ou próximo de zero.**

Antes de adicionar qualquer camada:

> **Isso resolve um problema que o BUSIVS BOT tem agora?**

Stack atual:

```text
Telegram
   ↓
Python + python-telegram-bot
   ↓
JSON para dados permanentes
   ↓
Memória para estado temporário do ônibus
```

Dependências atuais:

```text
python-telegram-bot
python-dotenv
```

---

# Decisão arquitetural atual: sem SQL

**Decisão tomada antes da hospedagem:** não adicionar banco de dados neste momento.

Motivo: o BUSIVS trabalha principalmente com informação atual e de vida curta.

Dados que precisam permanecer:

```text
horários → JSON
pontos   → JSON
rotas    → JSON
```

Dados que devem ser temporários:

```text
última confirmação
horário da confirmação
ponto anterior
sentido inferido
próximo ponto
contexto do bloco operacional atual
```

O sistema não precisa saber onde o ônibus estava muitas horas atrás para responder onde ele está agora.

SQL/SQLite só deve entrar quando existir necessidade real de histórico, por exemplo:

- calcular tempos médios reais entre pontos;
- estudar atrasos por faixa de horário;
- guardar histórico de viagens;
- produzir estatísticas;
- calibrar automaticamente estimativas;
- manter controles de abuso de longo prazo.

Até lá, **estado em memória é uma escolha intencional, não uma limitação a ser corrigida automaticamente**.

---

# Ciclo de vida do estado: blocos operacionais

O bot não deve ser reiniciado várias vezes ao dia apenas para apagar localização antiga.

O processo pode ficar rodando 24h. Quem expira é o **contexto do ônibus** quando ele deixa de pertencer ao bloco operacional atual.

## Conceito

Cada saída é uma volta, mas várias voltas próximas podem fazer parte do mesmo bloco de circulação.

Exemplo da manhã:

```text
06:25 Garagem
↓
06:50 RU
↓
07:10 RU
↓
07:25 RU
↓
07:40 RU
↓
07:55 RU
```

Essas saídas são consecutivas e podem compartilhar o mesmo contexto em memória.

Depois existe uma lacuna relevante até a retomada seguinte. Nesse ponto o contexto anterior deixa de ser útil e pode ser descartado.

## Regra atual

Implementada em `src/passagens.py`:

```text
intervalo entre saídas <= 60 min
→ mesmo bloco operacional
→ mantém contexto

intervalo entre saídas > 60 min
→ quebra de bloco
```

O limite atual é:

```text
LIMITE_INTERVALO_BLOCO_MINUTOS = 60
```

A quebra não apaga uma confirmação enquanto a viagem anterior ainda pode estar em andamento. A limpeza ocorre quando o sistema já entrou na lacuna operacional ou quando o próximo bloco começou.

Também continua valendo:

```text
confirmação de dia anterior
→ limpa
```

## Comportamento esperado

```text
MESMO BLOCO
06:25 → 06:50 → 07:10 → 07:25 → 07:40 → 07:55
→ contexto pode continuar em memória

LACUNA GRANDE
fim da circulação do bloco anterior → próxima retomada
→ estado antigo expira

NOVO BLOCO
primeira saída após a lacuna
→ não carrega localização do bloco anterior
```

Isso é diferente de um TTL rígido. O estado não é apagado só porque passaram 30 minutos ou porque começou uma nova saída.

A janela de **30 minutos** continua existindo apenas como proteção para considerar uma confirmação recente em situações de possível atraso e no bloqueio de registros fora de circulação.

Resumo da decisão:

> **O histórico em memória vale enquanto ele pertence ao mesmo bloco operacional. O fim do bloco é a fronteira natural de expiração.**

---

# Onde mexer?

## Horários

```text
data/horarios_letivo.json
```

Regras e estados derivados dos horários:

```text
src/horarios.py
```

## Pontos

```text
data/pontos.json
```

## Sequência da rota

```text
data/rotas.json
```

## Estado temporário, colaboração e "Onde está o ônibus?"

```text
src/passagens.py
```

Aqui ficam:

- última confirmação;
- tempo desde a confirmação;
- integração entre horário e rota;
- ciclo de vida por blocos operacionais;
- proteção contra passagem fora de circulação;
- localização apresentada ao usuário.

## Sentido e próximo ponto

```text
src/rota.py
```

## Telegram: menus, comandos e callbacks

```text
src/bot.py
```

## Testar rota

```bash
python -m unittest tests/test_rota.py
```

Simulador:

```bash
python tests/simular_rota.py
```

---

# Visão atual do produto

O BUSIVS BOT é um bot de Telegram para estudantes da UFRB - Campus Cruz das Almas.

Hoje ele responde principalmente:

1. Qual é o próximo horário do circular?
2. Existe uma viagem provavelmente em andamento?
3. Onde ocorreu a última confirmação útil?
4. Qual o sentido e o próximo ponto?
5. O ônibus provavelmente está no retorno?
6. O percurso provavelmente terminou?
7. Qual é a próxima saída?
8. Existe indício de atraso?

Sempre distinguir:

- **confirmação real**;
- **estimativa por horário**;
- **inferência de possível atraso**.

Nunca apresentar estimativa como certeza.

---

# Autenticação

Autenticação institucional continua adiada.

No protótipo:

- consulta é pública;
- informar passagem é público;
- `telegram_id` pode ser mantido internamente;
- abuso é tratado primeiro com regras simples de contexto e horário.

Autenticação só deve ser estudada se surgir um problema real que as regras atuais não consigam resolver.

---

# Ônibus

## Principal

Implementado e funcional.

## Micro

Ainda não implementado.

---

# Etapas concluídas

```text
Etapa 1  - Base do bot                              ✅
Etapa 2  - Horários fixos do Principal             ✅
Etapa 3  - Pontos / rota / sentido / próximo ponto ✅
Etapa 4  - Informar passagem                       ✅ protótipo
Etapa 5  - Localização / tempo / estados / proteção ✅ protótipo validado
Etapa 5.5- Ciclo de vida por blocos operacionais   ✅ pré-hospedagem
```

---

# Estados da viagem baseados em horário

O Principal trabalha atualmente com:

```text
1. viagem possivelmente em andamento
2. percurso de retorno
3. provavelmente aguardando na origem
4. próxima saída prevista
```

Exemplo da saída de 10:00:

```text
10:00–10:20 → viagem possivelmente em andamento
10:25–10:40 → percurso de retorno
10:40–11:30 → provavelmente na Garagem
11:30       → próxima saída
```

São aproximações, não GPS.

---

# Rota validada

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

Biblioteca aparece duas vezes. Nunca inferir sentido apenas pelo nome do ponto.

Exemplos:

```text
Pavilhão I → Biblioteca = RUA
Portão 1 → Biblioteca   = RU
Canãa → Portão 1        = RU
```

---

# Proteção contra registros fora de circulação

Implementada e testada.

Regra atual:

```text
ônibus aguardando próxima saída
+
sem confirmação válida nos últimos 30 minutos
=
bloquear nova passagem
```

A margem de 30 minutos preserva a possibilidade de atraso real.

Essa regra de proteção é independente do tempo de vida do bloco operacional.

---

# Possível atraso - regra experimental

Ainda restrita ao primeiro cenário estudado:

```text
janela: 10:15 até 10:20
último ponto: Biblioteca ou Pavilhão II
sentido: RUA
previsão Portão 1: por volta de 10:20
```

Não generalizar antes de observar uso real.

---

# Testes já realizados

## Automáticos

A rota cobre:

- Biblioteca na ida;
- Biblioteca no retorno;
- Canãa → Portão 1;
- pontos opcionais usados ou pulados;
- transições inválidas;
- ponto inexistente.

## Manuais

Já foram testados com sucesso:

- informar passagem;
- tempo decorrido;
- sentido;
- próximo ponto;
- viagem baseada em horário;
- percurso de retorno;
- provável espera na Garagem;
- próxima saída;
- bloqueio fora de circulação.

## Últimos testes antes de hospedar

Validar agora especificamente os blocos operacionais:

1. registrar passagem durante o bloco `06:25 → 07:55` e confirmar que uma nova saída do mesmo bloco não apaga o contexto;
2. confirmar que a localização ainda pode evoluir entre viagens consecutivas do mesmo bloco;
3. entrar numa lacuna maior que 60 minutos depois da viagem anterior terminar e verificar que o estado antigo é descartado;
4. iniciar o próximo bloco sem ter consultado o bot durante a lacuna e confirmar que o estado anterior também é descartado;
5. validar virada de dia;
6. repetir o bloqueio de passagem fora de circulação;
7. rodar novamente `python -m unittest tests/test_rota.py`.

---

# Pré-hospedagem

Checklist:

```text
[ ] validar blocos operacionais em teste local
[ ] rodar testes de rota novamente
[ ] revisar mensagens principais do Telegram
[ ] confirmar .env fora do Git
[ ] confirmar requirements.txt mínimo
[ ] decidir plataforma de hospedagem
[ ] configurar TELEGRAM_BOT_TOKEN na plataforma
[ ] manter processo Python ativo 24h
[ ] validar timezone UTC-3 no ambiente hospedado
[ ] fazer teste real com poucos alunos
```

A hospedagem não precisa de:

- PostgreSQL;
- Redis;
- frontend;
- reinicializações programadas várias vezes ao dia;
- persistência de localização por SQL;
- Docker, salvo se a plataforma escolhida realmente exigir ou simplificar.

O bot deve ficar online 24h e deixar o próprio ciclo operacional controlar a validade do estado.

---

# Próximas etapas depois de colocar online

A prioridade deve ser observar uso real antes de ampliar a arquitetura.

```text
Hospedagem / teste com alunos                  ⏭️ próximo
Etapa 6  - Principal + Micro                   ⏳
Etapa 7  - NFC                                 ⏳
Etapa 8  - Desvios dos portões                 ⏳
Etapa 9  - Modo de férias                      ⏳
Etapa 10 - Autenticação institucional          ⏳ se necessária
Etapa 11 - Avisos e alertas automáticos        ⏳ pós-protótipo
```

Sugestão atual: **não começar o Micro antes de colocar o Principal online e observar o comportamento do protótipo com usuários reais.**

---

# Quando reconsiderar persistência

Reavaliar SQLite somente quando uma destas necessidades surgir:

```text
histórico de passagens de longo prazo
métricas de uso
tempos médios entre pontos
estimativas baseadas em dados reais
estatísticas de atraso
estado sobrevivendo a reinícios por necessidade funcional
controle de abuso de longo prazo
```

Até lá:

> **JSON guarda o que é permanente. Memória guarda o contexto do bloco operacional atual.**
