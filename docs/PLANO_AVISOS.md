# Plano de Avisos — BUSIVS BOT

Documento de desenho da próxima frente de melhorias do BUSIVS.

## Ideia atual

O botão `📢 Avisos` terá comportamento diferente para administrador e usuários comuns.

### Administrador

Apenas o Telegram ID de Gabriel será autorizado a administrar avisos.

Ao tocar em `📢 Avisos`, o administrador poderá:

- criar um aviso digitando o texto;
- escolher um aviso pré-editado;
- visualizar os avisos ativos;
- remover um aviso ativo;
- substituir/editar um aviso existente.

Não é necessário cadastrar todos os usuários do bot para essa primeira versão. Basta persistir/configurar o Telegram ID autorizado para administração.

### Usuários comuns

Para usuários comuns, o botão `📢 Avisos` não abrirá uma tela de administração nem exigirá interação adicional.

Os avisos ativos serão exibidos diretamente no menu principal, abaixo da área de botões, para que a informação fique visível assim que o usuário abrir/interagir com o BUSIVS.

A primeira versão deve aceitar poucos avisos simultâneos, preferencialmente:

```text
máximo de 2 ou 3 avisos ativos
```

Isso evita poluir o menu e mantém a interface objetiva.

## Fluxo conceitual

```text
Gabriel toca em 📢 Avisos
        ↓
Telegram ID é validado
        ↓
menu administrativo
        ↓
criar aviso / escolher pré-editado / remover aviso
        ↓
aviso salvo no estado compartilhado
        ↓
usuário comum abre o menu
        ↓
avisos ativos aparecem abaixo dos botões
```

## Decisão de arquitetura

Para a primeira versão de Avisos, não criar cadastro geral de usuários nem lista de inscritos apenas para exibir comunicados no menu.

Persistir somente:

```text
ADMIN_TELEGRAM_ID
avisos_ativos (máximo 2 ou 3)
```

O `ADMIN_TELEGRAM_ID` deve ficar em configuração/secret de ambiente, não hardcoded no código público.

Os avisos ativos podem utilizar o Durable Object já existente ou um estado administrativo separado, dependendo do desenho final. Evitar banco adicional enquanto não houver necessidade concreta.

## Avisos pré-editados — exemplos a avaliar

```text
🚪 Portão 1 fechado
🚪 Portão 2 fechado
⚠️ Circular operando com atraso
🛠️ Circular temporariamente fora de operação
🚌 Rota alterada temporariamente
📅 Horários especiais hoje
```

Avisos de fechamento de portão não devem ser apenas texto: posteriormente precisam se integrar ao estado operacional de rota e às estimativas de tempo.

## Ponto importante

Esta ideia substitui a necessidade inicial de guardar o `chat_id` de todos os usuários apenas para avisos visíveis no menu.

Disparo proativo de notificações para usuários continua sendo uma melhoria futura separada. Caso essa função seja implementada, aí sim será necessário manter uma lista de `chat_id`s/inscritos e lidar com usuários que bloquearem o bot.
