# Pós-protótipo — Segurança e confiabilidade colaborativa

Esta frente deve ser tratada depois da consolidação do protótipo principal. O objetivo é impedir que o mecanismo colaborativo de marcação de ponto seja degradado por excesso de cliques, trotes, automação maliciosa ou tentativa deliberada de manipular a localização do circular.

## Situação atual

Hoje o BUSIVS já possui algumas proteções operacionais:

- rejeição de duplicidade imediata do mesmo ponto;
- validação de plausibilidade física entre pontos;
- histórico operacional curto para recuperar sequências coerentes;
- expiração de confirmação antiga entre voltas;
- bloqueio de registros em situações incompatíveis com a operação prevista.

Essas proteções cuidam principalmente da coerência da rota. Elas não são suficientes para abuso em escala.

## Problema a resolver

Não existe benefício em dezenas de alunos confirmarem o mesmo ponto em poucos segundos. Depois que uma confirmação confiável foi recebida, novas confirmações equivalentes dentro de uma janela curta devem ter valor reduzido ou ser ignoradas.

Também devem ser considerados cenários como:

- um usuário marcando muitos pontos em sequência;
- dezenas de usuários marcando o mesmo ponto simultaneamente;
- grupos tentando deslocar artificialmente a localização do ônibus;
- scripts/bots disparando callbacks repetidamente;
- trotes com pontos incompatíveis;
- alternância proposital entre pontos conflitantes;
- tentativa de sobrecarregar Worker, Telegram Bot API ou Durable Object;
- abuso recorrente vindo do mesmo Telegram ID.

## Diretrizes para implementação futura

### 1. Janela de confirmação por ponto

Quando um ponto já tiver sido confirmado recentemente, novas confirmações do mesmo ponto durante uma pequena janela não precisam alterar novamente o estado.

Exemplo conceitual:

```text
13:20:00 Biblioteca confirmada
13:20:05 nova confirmação Biblioteca
13:20:12 nova confirmação Biblioteca
...

→ estado continua sendo Biblioteca às 13:20
→ cliques extras não geram escrita desnecessária
```

A janela deve ser calibrada com uso real. Não definir um valor rígido antes de observar o comportamento em produção.

### 2. Rate limit por Telegram ID

Cada usuário deve ter um limite razoável de marcações em uma janela curta.

Objetivo:

```text
uso normal
→ nenhuma fricção

muitos cliques em poucos segundos
→ ignorar / aplicar cooldown
```

Não é necessário cadastro institucional para isso; o Telegram ID pode ser usado apenas como identificador técnico temporário.

### 3. Rate limit por ponto

Além do usuário, considerar limite agregado por ponto.

Exemplo:

```text
50 alunos marcam Biblioteca em 20 segundos
→ não realizar 50 atualizações equivalentes
→ consolidar como uma única confirmação operacional recente
```

Isso reduz escrita no Durable Object e chamadas/respostas desnecessárias.

### 4. Confirmações conflitantes

Marcações concorrentes de pontos diferentes não devem simplesmente sobrescrever o estado pela ordem de chegada.

Avaliar futuramente um mecanismo simples de confiança baseado em:

- coerência com a rota;
- tempo desde a última confirmação confiável;
- distância lógica entre os pontos;
- quantidade de confirmações compatíveis;
- histórico recente do usuário apenas quando necessário.

Evitar sistemas complexos de reputação antes de existir necessidade real.

### 5. Detecção de rajadas anormais

O sistema deve conseguir perceber padrões improváveis, por exemplo:

```text
mesmo usuário
→ 10 pontos em poucos segundos

muitos usuários
→ pontos opostos da rota em sequência muito rápida

mesmo ponto
→ volume muito acima do uso normal
```

A primeira reação deve ser conservadora: ignorar excesso e preservar o último estado plausível.

### 6. Cooldown e bloqueio temporário

Para abuso evidente, considerar bloqueio temporário por Telegram ID.

Não começar com banimento permanente.

Possíveis níveis:

```text
nível 1 → ignorar duplicatas
nível 2 → cooldown temporário
nível 3 → bloquear marcações por alguns minutos
nível 4 → intervenção administrativa se abuso recorrente
```

### 7. Proteção contra invasão / automação

Manter e revisar:

- secret do webhook;
- secrets fora do Git;
- validação de callbacks aceitos;
- rejeição de payloads inesperados;
- limites de tamanho de entrada;
- endpoints administrativos protegidos;
- ADMIN_TELEGRAM_ID para funções privilegiadas;
- logs de erros e padrões anormais sem armazenar histórico pessoal desnecessário.

### 8. Modo de proteção emergencial

Avaliar um comando administrativo pelo Telegram para situações de abuso intenso, por exemplo:

```text
/protecao
```

Esse modo poderia temporariamente:

- aumentar cooldown;
- reduzir frequência de atualização do mesmo ponto;
- bloquear marcações colaborativas e manter apenas horários/avisos;
- permitir reativação pelo administrador.

Só implementar se houver necessidade real observada.

## Princípio de privacidade

Não transformar segurança em rastreamento permanente de usuários.

Guardar somente o mínimo necessário para proteger o serviço, preferencialmente com expiração curta:

```text
Telegram ID técnico
últimos timestamps necessários para rate limit
contadores temporários
bloqueio temporário quando aplicável
```

Não criar perfil permanente de deslocamento ou uso sem necessidade concreta.

## Prioridade pós-protótipo

Esta frente deve entrar no roadmap como:

```text
Segurança e confiabilidade colaborativa
→ deduplicação em escala
→ rate limit por usuário
→ rate limit por ponto
→ proteção contra trote
→ proteção contra rajadas/invasão
→ conflito entre confirmações
→ cooldown/bloqueio temporário
→ modo de proteção administrável pelo Telegram
```

A implementação deve continuar seguindo o princípio do BUSIVS: começar simples, observar o uso real e adicionar apenas as proteções que resolverem problemas concretos.
