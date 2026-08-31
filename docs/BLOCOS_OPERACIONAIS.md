# Blocos operacionais — BUSIVS BOT

> Regra de produção para separar as voltas do Circular Principal em contextos operacionais. Revisado em 31/08/2026 contra `cloudflare/src/dados.py`.

## 1. Conceito

Um bloco operacional representa um ciclo de trabalho do veículo que executa uma ou mais voltas e termina quando o ônibus retorna plausivelmente à Garagem após a última volta do conjunto.

A Garagem não é um ponto colaborativo comum da rota. Ela representa origem/encerramento de blocos e pode ser inferida quando a janela operacional realmente terminou ou marcada manualmente pela administração.

Dentro de um bloco, o horário é referência. Ele não deve apagar evidência real nem trocar de volta sozinho.

---

## 2. Blocos do Circular Principal

| Bloco | Início | Última referência | Fechamento-base |
|---|---:|---:|---:|
| Manhã inicial | 06:25 | 07:55 | 08:35 |
| Manhã intermediário | 09:35 | 10:00 | 10:35 |
| Almoço | 11:30 | 12:20 | 13:00 |
| Início da tarde | 13:00 | 14:00 | 14:40 |
| Tarde intermediário | 15:35 | 16:00 | 16:35 |
| Fim da tarde | 17:30 | 18:15 | 18:55 |
| Noite experimental | 20:00 | 20:00 | 20:25 |
| Noite 1 | 20:40 | 20:40 | 21:10 |
| Noite 2 | 21:40 | 21:40 | 22:10 |
| Noite 3 | 22:30 | 22:30 | 23:00 |

### 20:00 — experimental

A referência das 20:00 existe no código, mas é explicitamente experimental:

```text
20:00 — saída da Garagem
previsão Portão 1: 20:10–20:15
fechamento do bloco: 20:25
⚠️ pode não ocorrer; referência baseada em rotina anterior
```

Não apresentá-la como operação garantida.

### Fluxos com duas referências

```text
09:35 — saída da Garagem
10:00 — saída do RU / última volta
→ percurso de retorno sentido Garagem
→ encerra bloco

15:35 — saída da Garagem
16:00 — saída do RU / última volta
→ percurso de retorno sentido Garagem
→ encerra bloco
```

Os horários 20:00, 20:40, 21:40 e 22:30 são blocos noturnos independentes.

---

## 3. Cálculo do fechamento

Quando o bloco não possui `fim` explícito, o fechamento-base usa a previsão máxima de chegada ao Portão 1 da última volta e acrescenta tolerância de retorno:

- durante o dia: +15 min;
- à noite: +10 min.

O bloco experimental das 20:00 possui `fim: 20:25` explicitamente configurado.

O horário é uma estimativa operacional. Confirmação colaborativa válida pode demonstrar atraso real enquanto a regra de extensão permitir.

---

## 4. Pico e extensão por atraso

Quando a última volta do bloco é classificada como pico, confirmação válida próxima do fechamento pode estender o contexto em até 10 minutos.

Quando já existe bloco seguinte, o estado antigo pode sobreviver apenas dentro da pequena tolerância definida pela regra de transição. Isso absorve atraso real sem deixar uma volta antiga contaminar indefinidamente a nova operação.

Se surgir confirmação compatível com o bloco novo depois que ele começou, o BUSIVS limpa o histórico anterior antes de registrar o novo ponto.

Exemplo:

```text
12:20 — última referência do almoço
12:50 — confirmação real mostra atraso
13:00 — abertura do bloco seguinte
13:02 — Pavilhão I compatível com nova saída

=> abandona contexto anterior
=> Pavilhão I vira primeira confirmação limpa do bloco das 13:00
```

RU sozinho não força essa troca porque pode ser fim da volta anterior ou espera. Biblioteca continua ambígua e depende de contexto.

---

## 5. Referência dentro do bloco

O relógio sozinho não avança a referência da volta.

Exemplo:

```text
11:55 — referência atual
12:05 — nenhuma nova evidência
=> continua 11:55
```

Uma confirmação real pode demonstrar avanço/reinício quando a sequência de rota e uma nova saída oficial forem compatíveis.

A administração pode selecionar explicitamente uma referência oficial do bloco pelo controle `🧭 Escolher volta de referência`.

Isso substitui a ideia antiga de simplesmente “voltar para a volta anterior”: o administrador escolhe qual volta é a referência correta.

---

## 6. RU e reinício

RU confiável encerra a volta atual.

RU não inicia a próxima sozinho.

Um ponto anterior na sequência só pode representar nova volta quando houver contexto compatível com uma saída oficial posterior.

Exemplo inválido:

```text
Torre / COTEC
Pavilhão II
sem nova saída oficial entre os registros
=> não tratar como reinício normal
```

Na última volta do dia não existe nova saída posterior, então a rota não pode reiniciar artificialmente depois das 22:30.

---

## 7. Sentido da rota

Fora da Biblioteca, diversos pontos determinam naturalmente o sentido pelo lugar na rota.

Exemplos:

```text
Portão 2 -> sentido RUA
Portão 1 -> sentido RU
Torre / COTEC -> sentido RU
```

Se ponto inequívoco for primeira confirmação de um bloco, ele pode estabelecer sentido e próximo ponto.

RU permanece especial e Biblioteca exige contexto próprio porque aparece duas vezes na rota.

---

## 8. Última volta e retorno sentido Garagem

Na última volta do bloco, a comunicação correta é:

```text
percurso de retorno sentido Garagem
```

Evitar mensagem que apenas diga “retornando para a Garagem” se isso puder sugerir que o ônibus deixou de atender os pontos ainda existentes no percurso.

A localização deve continuar aproveitando confirmações reais compatíveis durante o retorno.

Quando o bloco termina de fato e não há evidência válida que sustente atraso, a resposta passa para Garagem/próxima saída.

---

## 9. Janela de registro colaborativo

Confirmação de ponto do Principal só pode ser aceita enquanto existir bloco operacional ativo.

Fora dessas janelas:

- o menu não deve oferecer registro do Principal como disponível;
- callbacks antigos/chamadas diretas devem ser rejeitados;
- a regra também vale para administração quanto ao registro normal de ponto.

A administração ainda possui controles próprios de correção/referência e encerramento.

Nos fins de semana, sem operação regular cadastrada, o registro colaborativo do Principal permanece indisponível.

---

## 10. Localização fora dos blocos

`Onde está o ônibus?` continua útil fora da janela de registro.

Entre blocos:

```text
provavelmente na Garagem
+ próxima saída
```

Depois do último bloco:

```text
rotina do dia encerrada
+ próxima saída no próximo dia útil
```

A primeira saída oficial permanece **06:25**. Uma eventual janela de pré-saída não altera o horário oficial nem abre registro antes do início real do bloco.

---

## 11. Administração — Garagem

O botão:

```text
🅿️ Garagem / Encerrar bloco
```

encerra manualmente o bloco identificado e deve ser usado quando o administrador possui evidência operacional de que aquele ciclo terminou.

Encerrar bloco não deve criar uma nova volta artificial.

---

## 12. Avisos operacionais

Avisos são associados a contexto/bloco e expiram conforme a regra operacional para evitar informação velha ativa.

Um aviso de um bloco noturno não deve atravessar automaticamente para o próximo:

```text
20:00 -> não atravessa 20:40
20:40 -> não atravessa 21:40
21:40 -> não atravessa 22:30
22:30 -> encerra no fim do dia
```

Se a ocorrência continuar, a administração publica novamente.

---

## 13. Fonte da configuração

Blocos e horários:

```text
cloudflare/src/dados.py
BLOCOS_PRINCIPAL
HORARIOS["principal"]
```

Fechamento compartilhado:

```text
cloudflare/src/blocos_operacionais.py
```

Transição entre blocos:

```text
cloudflare/src/transicao_bloco.py
```

Expiração/referência:

```text
cloudflare/src/expiracao_volta.py
cloudflare/src/volta_referencia.py
```

Não criar um conceito paralelo de bloco em outra camada sem decisão explícita e teste de regressão.
