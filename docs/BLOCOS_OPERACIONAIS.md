# Blocos operacionais — BUSIVS BOT

Este documento registra a regra usada em produção para separar as voltas do Circular Principal em blocos operacionais.

## Conceito

Um bloco operacional representa um ciclo de trabalho do veículo que executa uma ou mais voltas e termina quando o ônibus retorna plausivelmente à Garagem após a última volta do conjunto.

A Garagem não é um ponto colaborativo da rota. O retorno à Garagem é inferido pelo horário quando não existe confirmação real suficiente.

Nos blocos **09:35–10:00** e **15:35–16:00**, a primeira referência sai da Garagem e a segunda sai do RU / Residências. A volta das 10:00 ou 16:00 é a última volta do respectivo bloco; depois dela o veículo retorna à Garagem e encerra o bloco.

## Blocos do Circular Principal

| Bloco | Início | Última volta de referência | Fechamento-base estimado |
|---|---:|---:|---:|
| Manhã inicial | 06:25 | 07:55 | 08:35 |
| Manhã intermediário | 09:35 | 10:00 | 10:35 |
| Almoço | 11:30 | 12:20 | 13:00 |
| Início da tarde | 13:00 | 14:00 | 14:40 |
| Tarde intermediário | 15:35 | 16:00 | 16:35 |
| Fim da tarde | 17:30 | 18:15 | 18:55 |
| Noite 1 | 20:40 | 20:40 | 21:10 |
| Noite 2 | 21:40 | 21:40 | 22:10 |
| Noite 3 | 22:30 | 22:30 | 23:00 |

Fluxos especiais:

```text
09:35 — saída da Garagem
10:00 — saída do RU / última volta
→ retorno à Garagem
→ encerra o bloco

15:35 — saída da Garagem
16:00 — saída do RU / última volta
→ retorno à Garagem
→ encerra o bloco
```

Os horários 20:40, 21:40 e 22:30 pertencem ao mesmo turno noturno, mas são três blocos independentes: cada um começa e encerra sua operação separadamente.

## Cálculo do fechamento

O fechamento-base usa a previsão máxima de chegada ao Portão 1 da última volta do bloco e acrescenta uma tolerância para o retorno:

- durante o dia: +15 min;
- à noite: +10 min.

O horário é uma estimativa. Uma confirmação colaborativa válida pode demonstrar atraso real.

## Horários de pico

Quando a última volta do bloco é de pico, uma confirmação válida feita perto do fechamento pode estender o bloco em até 10 minutos.

Quando já existe um bloco seguinte, o estado antigo pode sobreviver no máximo 5 minutos após a abertura desse novo bloco. Isso permite absorver atraso real sem deixar a volta anterior contaminar indefinidamente a nova operação.

Se surgir uma confirmação compatível com o bloco novo depois que ele começou, o BUSIVS abandona o histórico do bloco anterior antes de registrar o novo ponto. A nova confirmação passa a ser a primeira referência limpa daquele bloco.

Exemplo do almoço:

```text
12:20 — última volta do bloco
12:50 — confirmação real mostra atraso
13:00 — fechamento-base / início do bloco seguinte
13:02 — Pavilhão I compatível com a nova saída

→ abandona histórico do bloco anterior
→ Pavilhão I vira primeira confirmação do bloco das 13:00
```

RU sozinho não força essa troca porque pode representar fim da volta anterior ou espera. Biblioteca pode iniciar o novo contexto, mas continua com tratamento especial de sentido por aparecer na ida e no retorno.

## Sentido da rota

Fora da Biblioteca, a maioria dos pontos já determina naturalmente o sentido pela própria posição na rota.

Exemplos:

```text
Portão 2 → sentido RUA
Portão 1 → sentido RU
Torre / COTEC → sentido RU
```

Se um ponto inequívoco for a primeira confirmação do bloco, o BUSIVS já usa essa posição para definir sentido e próximo ponto. RU permanece ambíguo e Biblioteca mantém sua regra contextual específica.

No Circular Principal, um ponto anterior na sequência da rota só pode representar uma nova volta se uma nova saída oficial tiver ocorrido depois da última confirmação.

Exemplo inválido:

```text
Torre / COTEC
Pavilhão II
sem nova saída oficial entre as confirmações
→ rejeitar
```

Na última volta do dia não existe nova saída posterior. Portanto, depois do encerramento da volta das 22:30, a rota não pode reiniciar artificialmente.

## Janela de registro colaborativo

Uma confirmação de ponto do Circular Principal só pode ser aceita enquanto existir um bloco operacional ativo.

Fora dessas janelas, o BUSIVS não abre o seletor de pontos e o backend também rejeita callbacks antigos ou chamadas diretas com `fora_circulacao`. A regra vale igualmente para usuários comuns e administradores.

Exemplo do fim do dia:

```text
22:30 — início do último bloco
23:00 — fechamento-base
23:00 até o início do primeiro bloco do próximo dia
→ registro de ponto indisponível
```

Nos fins de semana, em que não há operação regular cadastrada, o registro colaborativo do principal também permanece indisponível.

## Resposta de localização fora dos blocos

`Onde está o ônibus?` continua útil mesmo quando o registro colaborativo está fechado.

Entre blocos do mesmo dia, o BUSIVS informa que o circular provavelmente está na Garagem e mostra a próxima saída. Depois do último bloco, informa que a rotina do dia encerrou e calcula a próxima saída no próximo dia útil. Aos fins de semana, informa que não há operação regular e aponta a próxima segunda-feira ou outro próximo dia útil.

Exemplos:

```text
09:00
→ provavelmente na Garagem
→ próxima saída: 09:35 — Garagem

00:30 de um dia útil
→ rotina anterior encerrada
→ provavelmente na Garagem
→ próxima saída: hoje às 06:25 — Garagem

sexta após o encerramento
→ rotina encerrada
→ próxima saída: segunda-feira às 06:25 — Garagem
```

A primeira saída oficial continua sendo **06:25**. O horário **06:20** é apenas o início da janela de pré-saída de 5 minutos. Dentro dessa janela, a resposta muda para “saída prevista em aproximadamente X min”, mas o registro colaborativo só abre quando o bloco realmente começa.

## Avisos

Avisos operacionais pertencem a um único bloco e expiram no **fechamento-base** desse bloco, sem extensão por atraso.

Mesmo que uma confirmação real mantenha temporariamente o estado da localização em horário de pico, o aviso encerra no horário-base. Se a ocorrência continuar, o administrador publica o aviso novamente.

Consequência no turno noturno:

```text
aviso criado no bloco das 20:40 → não atravessa para 21:40
aviso criado no bloco das 21:40 → não atravessa para 22:30
aviso criado no bloco das 22:30 → expira no encerramento do dia
```

Se um aviso for criado durante uma lacuna depois do encerramento de um bloco, ele é associado ao próximo bloco operacional.

## Fonte da configuração

Os limites oficiais dos blocos ficam em:

```text
cloudflare/src/dados.py
BLOCOS_PRINCIPAL
```

As regras compartilhadas de fechamento ficam em:

```text
cloudflare/src/blocos_operacionais.py
```

A transição limpa entre o estado antigo e uma confirmação compatível do bloco novo fica em:

```text
cloudflare/src/transicao_bloco.py
```

Módulos de expiração, avisos e ciclos noturnos devem usar essa definição central e não criar conceitos paralelos de bloco.
