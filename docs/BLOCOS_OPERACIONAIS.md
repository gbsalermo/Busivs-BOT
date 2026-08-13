# Blocos operacionais — BUSIVS BOT

Este documento registra a regra usada em produção para separar as voltas do Circular Principal em blocos operacionais.

## Conceito

Um bloco operacional representa um ciclo de trabalho do veículo que começa na Garagem, executa uma ou mais voltas e termina quando o ônibus retorna plausivelmente à Garagem após a última volta do conjunto.

A Garagem não é um ponto colaborativo da rota. O retorno à Garagem é inferido pelo horário quando não existe confirmação real suficiente.

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

Os horários 20:40, 21:40 e 22:30 pertencem ao mesmo turno noturno, mas são três blocos independentes: cada um começa e encerra na Garagem.

## Cálculo do fechamento

O fechamento-base usa a previsão máxima de chegada ao Portão 1 da última volta do bloco e acrescenta uma tolerância para o retorno:

- durante o dia: +15 min;
- à noite: +10 min.

O horário é uma estimativa. Uma confirmação colaborativa válida pode demonstrar atraso real.

## Horários de pico

Quando a última volta do bloco é de pico, uma confirmação válida feita perto do fechamento pode estender o bloco em até 10 minutos.

Quando já existe um bloco seguinte, o estado antigo pode sobreviver no máximo 5 minutos após a abertura desse novo bloco. Isso permite absorver atraso real sem deixar a volta anterior contaminar indefinidamente a nova operação.

Uma confirmação realizada depois da nova saída oficial pertence naturalmente ao novo contexto e não deve ser apagada pela tolerância aplicada à volta anterior.

Exemplo do almoço:

```text
12:20 — última volta do bloco
13:00 — fechamento-base / início do bloco seguinte

se houver confirmação válida muito recente da volta anterior:
→ tolerância máxima até aproximadamente 13:05

se surgir confirmação compatível com a saída de 13:00:
→ o novo bloco passa a ter prioridade
```

## Ordem da rota

No Circular Principal, um ponto anterior na sequência da rota só pode representar uma nova volta se uma nova saída oficial tiver ocorrido depois da última confirmação.

Exemplo válido:

```text
volta anterior termina
06:50 — nova saída oficial
Pavilhão I / Biblioteca / Pavilhão II
→ pode representar a nova volta
```

Exemplo inválido:

```text
Torre / COTEC
Pavilhão II
sem nova saída oficial entre as confirmações
→ rejeitar
```

Na última volta do dia não existe nova saída posterior. Portanto, depois do encerramento da volta das 22:30, a rota não pode reiniciar artificialmente.

## Avisos

Avisos operacionais pertencem a um único bloco e expiram no fechamento-base desse bloco, sem exceção.

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

Módulos de expiração, avisos e ciclos noturnos devem usar essa definição central e não criar conceitos paralelos de bloco.
