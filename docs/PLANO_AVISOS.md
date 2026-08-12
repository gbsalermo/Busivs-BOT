# Plano de Avisos — BUSIVS BOT

Documento de desenho da frente de Avisos do BUSIVS.

## Ideia atual

O botão `📢 Avisos` terá comportamento diferente para administrador e usuários comuns.

### Administrador

Apenas o Telegram ID configurado em `ADMIN_TELEGRAM_ID` será autorizado a administrar avisos.

Ao tocar em `📢 Avisos`, o administrador poderá:

- escolher um aviso pré-editado;
- criar um aviso personalizado;
- visualizar os avisos ativos;
- remover um aviso ativo;
- limpar todos os avisos.

A primeira versão aceita no máximo **3 avisos ativos** e avisos personalizados de até **280 caracteres**.

### Usuários comuns

Para usuários comuns, o botão `📢 Avisos` não abre painel administrativo.

Os avisos ativos são exibidos no menu principal, abaixo da mensagem que contém os botões.

## Avisos pré-editados

```text
🚪 Portão 1 fechado
🚪 Portão 2 fechado
⚠️ Circular operando com atraso
🛠️ Circular temporariamente fora de operação
🛠️ Circular quebrou em meio ao trajeto
🌧️ Tempo chuvoso, circular pode demorar mais do que o esperado
🚌 Rota alterada temporariamente
📅 Horários especiais hoje
✏️ Aviso personalizado
```

## Diretriz central: aviso não é necessariamente só texto

Os avisos foram divididos conceitualmente em dois grupos.

### Avisos informativos

Podem ser exibidos sem alterar diretamente a lógica principal.

Exemplo:

```text
aviso personalizado simples
```

### Avisos operacionais

Devem influenciar respostas relacionadas à operação.

Exemplos:

```text
Circular quebrou
→ a volta atual pode não ser concluída
→ última localização não garante que o veículo continue em movimento
→ próximas saídas podem atrasar ou ser canceladas

Circular fora de operação
→ localização anterior deixa de ser uma indicação confiável de movimento
→ próximas saídas podem não ocorrer até normalização

Circular com atraso
→ horários oficiais continuam sendo referência
→ previsões precisam ser apresentadas com ressalva

Tempo chuvoso
→ duração das voltas pode aumentar
→ horários seguintes podem ser afetados

Portão fechado
→ não é apenas aviso textual
→ rota e duração da volta podem mudar
→ integração completa será feita na etapa de rota operacional

Rota alterada
→ próximo ponto e estimativas da rota padrão podem não ser válidos

Horários especiais
→ grade padrão pode não representar integralmente a operação do dia
```

## Comportamento já aplicado na alpha

`Onde está o ônibus?` passa a exibir contexto operacional quando existir aviso relevante.

`Próximos horários` e a listagem por período passam a avisar quando uma ocorrência ativa puder afetar a volta atual ou as próximas.

Exemplo para quebra:

```text
A volta em andamento foi prejudicada por uma quebra.
Ela pode não ser concluída e as próximas saídas também podem sofrer atraso ou cancelamento.
```

A informação deve ser apresentada como possibilidade operacional, não como certeza sobre cancelamento das próximas viagens.

## Fluxo conceitual

```text
Administrador toca em 📢 Avisos
        ↓
Telegram ID é validado
        ↓
painel administrativo (0/3 ... 3/3)
        ↓
pré-editado ou personalizado
        ↓
aviso salvo no Durable Object
        ↓
usuário abre o menu
        ↓
avisos aparecem abaixo dos botões
        ↓
consultas operacionais consideram o impacto do aviso
```

## Decisão de arquitetura

Não criar cadastro geral de usuários nem banco adicional apenas para a primeira versão de Avisos.

Persistir somente:

```text
ADMIN_TELEGRAM_ID
avisos_ativos (máximo 3)
estado temporário de edição de aviso personalizado
```

Os avisos ativos usam o Durable Object já existente.

`ADMIN_TELEGRAM_ID` deve ficar em variável/secret de ambiente e nunca hardcoded no repositório.

## Evolução futura

Fechamento de Portão 1/2 e rota alterada precisam evoluir para um **estado operacional de rota**, alterando efetivamente sequência de pontos, plausibilidade e estimativas, não apenas mensagens.

Disparo proativo de notificações continua sendo uma melhoria separada. Somente nessa situação será necessário armazenar os `chat_id`s dos usuários inscritos.
