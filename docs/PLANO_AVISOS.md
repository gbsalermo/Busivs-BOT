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
→ o ponto continua sendo atendido
→ muda o acesso usado para ida/retorno
→ aumenta significativamente a duração da volta
→ pode gerar efeito cascata nas próximas saídas

Rota alterada
→ próximo ponto e estimativas da rota padrão podem não ser válidos

Horários especiais
→ grade padrão pode não representar integralmente a operação do dia
```

## Regra operacional dos portões

**Portão fechado significa acesso fechado, não ponto removido da rota.**

### Portão 1 fechado

O ônibus continua atendendo/parando no **Portão 1**. Porém, como o acesso pelo P1 está fechado, o retorno ao campus precisa ocorrer pelo **Portão 2**.

Fluxo conceitual:

```text
... → Portão 2 → trecho externo → Portão 1
                           ↓
                    atende o Portão 1
                           ↓
                 retorno excepcional
                           ↓
                       Portão 2
                           ↓
                    interior do campus
```

Consequências:

```text
- Portão 1 continua aparecendo como ponto válido;
- Portão 1 → Portão 2 passa a ser uma sequência operacional válida;
- a volta tende a ficar significativamente mais longa;
- previsões padrão deixam de ser confiáveis sem ajuste;
- a volta seguinte pode iniciar atrasada por efeito cascata.
```

### Portão 2 fechado

O ônibus continua atendendo/parando no **Portão 2**. O acesso normal pelo P2 não pode ser usado e o fluxo precisa ser feito pelo **Portão 1**.

Consequências:

```text
- Portão 2 continua aparecendo como ponto válido;
- o ônibus precisa usar o P1 como acesso operacional;
- a volta tende a ficar significativamente mais longa;
- previsões padrão precisam ser apresentadas com ressalva;
- horários posteriores podem sofrer atraso acumulado.
```

### Se ambos aparecerem como fechados

Esse estado deve ser tratado como **configuração operacional inválida/indeterminada** até existir informação concreta de qual acesso alternativo está sendo usado. O BUSIVS não deve inventar uma rota possível.

### Estimativa de atraso

Nesta etapa, **não adicionar um número fixo de minutos**. Ainda não há medição real suficiente para dizer quanto o desvio acrescenta.

Enquanto não houver dados:

```text
rota normal
→ mantém estimativas atuais

portão fechado
→ mantém horário oficial como referência
→ informa que a duração da volta está significativamente afetada
→ alerta que próximas saídas podem atrasar
→ evita apresentar a previsão padrão como se tivesse a mesma precisão
```

Quando houver observações reais, criar um adicional específico por cenário, em vez de chutar um valor.

## Comportamento já aplicado na alpha

`Onde está o ônibus?` exibe contexto operacional quando existir aviso relevante.

`Próximos horários` e a listagem por período avisam quando uma ocorrência ativa puder afetar a volta atual ou as próximas.

A validação colaborativa também passou a conhecer a primeira exceção de rota:

```text
Portão 1 fechado + última confirmação no P1 + nova confirmação no P2
→ sequência aceita como retorno operacional pelo Portão 2
```

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

Fechamento de Portão 1/2 e rota alterada precisam evoluir gradualmente para alterar também estimativas quantitativas conforme dados reais forem coletados.

Disparo proativo de notificações continua sendo uma melhoria separada. Somente nessa situação será necessário armazenar os `chat_id`s dos usuários inscritos.
