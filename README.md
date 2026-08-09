# BUSIVS BOT 🚌

Bot comunitário para auxiliar estudantes da UFRB - Campus Cruz das Almas a consultar horários e acompanhar a posição estimada do ônibus circular.

> Status: protótipo inicial em funcionamento local.

## Interface inicial

O primeiro fluxo do bot já está rodando via Telegram com o comando `/start` e menu por botões inline.

![Interface inicial do BUSIVS BOT](docs/images/interface-inicial.jpg)

## Objetivo

O BUSIVS BOT usa o Telegram como interface principal. Os horários e pontos são dados fixos; a informação dinâmica é a última passagem confirmada do ônibus e, a partir dela, a previsão para os próximos pontos.

A localização poderá ser confirmada de duas maneiras:

- manualmente pelo comando `/local`, escolhendo o ponto em botões do Telegram;
- por uma tag NFC instalada no ponto, que abre o Telegram já identificando aquele ponto.

## Veículos

### Principal

Ônibus circular principal. É considerado o veículo regular do sistema.

### Micro

Micro-ônibus de reforço. Pode não operar todos os dias.

Regra prevista para o beta:

- antes da primeira confirmação do dia: status `NAO_CONFIRMADO`;
- após primeira confirmação válida: status `ATIVO`;
- se passar a janela esperada da primeira saída sem confirmação: informar ao usuário que **provavelmente não está operando**, sem afirmar ausência como fato.

## Stack proposta

- Python
- python-telegram-bot
- SQLite
- JSON para pontos, rotas, horários e mensagens
- SMTP/e-mail institucional para autenticação
- NFC usando deep link do Telegram

## Princípios

- simples e eficaz;
- arquitetura cresce somente quando o problema crescer;
- custo operacional zero ou próximo de zero;
- evitar infraestrutura e dependências desnecessárias;
- priorizar soluções fáceis de manter em ambiente universitário.

## Documentação

- [Fluxo do Telegram](docs/FLUXO_TELEGRAM.md)
- [Roadmap até Beta](docs/ROADMAP_BETA.md)
- [Arquitetura](docs/ARQUITETURA.md)
- [Continuidade](CONTINUIDADE.md)
