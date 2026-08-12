# BUSIVS BOT 🚌

Bot comunitário para acompanhar o **Circular da UFRB — Campus Cruz das Almas** pelo Telegram, combinando horários oficiais, regras da rota e confirmações colaborativas dos estudantes.

> **Status:** versão funcional em produção com Cloudflare Workers, Telegram Webhook e Durable Object.

## O problema

Quem depende do circular muitas vezes fica sem saber se o ônibus:

- já passou;
- está atrasado;
- está retornando;
- ainda está na origem;
- está perto de determinado ponto;
- terá reforço do micro-ônibus naquele período.

O BUSIVS foi criado para reduzir essa incerteza sem exigir GPS, aplicativo próprio ou infraestrutura cara.

## A solução

O bot usa três fontes principais de contexto:

```text
horários oficiais
+ regras da rota
+ confirmações colaborativas
```

A partir disso, consegue informar a última passagem registrada, estimar sentido e próximo ponto, mostrar próximas saídas e sinalizar situações operacionais importantes.

O sistema diferencia explicitamente **confirmação real** de **estimativa baseada no horário**.

## Recursos atuais

Pelo Telegram, o usuário pode:

- consultar onde o Circular Principal foi visto por último;
- informar em qual ponto o veículo acabou de passar;
- consultar próximas voltas;
- listar horários por período;
- consultar a rota;
- acompanhar o Micro-ônibus de reforço quando estiver operando;
- informar pontos do Principal e do Micro separadamente;
- visualizar avisos operacionais ativos;
- consultar ajuda e instruções de uso.

O sistema também possui:

- estados independentes para Principal e Micro;
- tratamento contextual da Biblioteca, que aparece duas vezes na rota;
- proteção contra confirmações duplicadas;
- proteção contra saltos fisicamente improváveis;
- expiração de estados antigos conforme o ciclo operacional;
- pré-saída e espera na origem;
- avisos temporários por bloco operacional;
- painel administrativo restrito ao administrador.

## Interface do bot

Menu principal:

```text
🚌 Onde está o ônibus?
📍 Informar ponto atual
⏰ Próximos horários
📋 Listar horários
🚐 Confirmar que micro está rodando
❓ Ajuda
```

Quando o micro é confirmado:

```text
🚐 Micro em operação ✅
```

O administrador também visualiza:

```text
📢 Avisos
```

## Localização colaborativa

Quando um estudante vê o ônibus passar, seleciona o ponto correspondente.

Essa informação alimenta um estado operacional compartilhado e temporário. A partir da sequência de pontos, o BUSIVS consegue estimar:

- sentido do veículo;
- próximo ponto esperado;
- ida ou retorno;
- contexto da volta atual.

O projeto não foi desenhado para rastrear usuários nem manter histórico permanente de localização.

## Circular Principal

O Principal continua sendo o veículo de referência do sistema.

Funcionalidades implementadas incluem:

- horários oficiais;
- próximas voltas;
- listagem por manhã, almoço, tarde e noite;
- rota completa;
- localização colaborativa;
- sentido e próximo ponto;
- espera na origem;
- pré-saída da Garagem;
- tolerância para atrasos reais;
- contexto entre viagens próximas;
- proteção de plausibilidade temporal.

## Micro-ônibus de reforço 🚐

O micro é tratado como **reforço**, não como substituto do Circular Principal.

Ele pode ou não operar em determinado dia. Por isso, qualquer usuário pode confirmar que viu o micro rodando.

Depois da confirmação:

- o botão muda para `🚐 Micro em operação ✅`;
- o estado do micro passa a ser acompanhado separadamente;
- o usuário escolhe se viu o Principal ou o Micro ao informar um ponto;
- `Onde está?` mostra os dois veículos;
- `Próximos horários` inclui as referências do micro.

Horários oficiais cadastrados:

```text
MANHÃ
07:25 — Garagem
07:40 — RU / Residências
07:55 — RU / Residências

MEIO-DIA
11:30 — Garagem
11:55 — RU / Residências
12:20 — RU / Residências
```

A última volta do meio-dia termina às **12:45**, com carência operacional até **13:00**.

Quando ativado durante a escala oficial, o estado do micro expira automaticamente às 13:00. Fora dessa faixa, uma operação extraordinária pode permanecer ativa até desativação administrativa.

## Avisos operacionais 📢

O administrador pode publicar avisos como:

- Portão 1 fechado;
- Portão 2 fechado;
- circular operando com atraso;
- circular temporariamente fora de operação;
- quebra durante o trajeto;
- tempo chuvoso;
- superlotação;
- micro está rodando;
- rota alterada;
- horários especiais;
- aviso personalizado.

Avisos ativos aparecem automaticamente para os usuários.

O aviso `🚐 Micro está rodando!` é apenas informativo e não altera o estado do micro.

## Rota principal cadastrada

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

Como a Biblioteca aparece duas vezes, o sistema usa contexto temporal e sequência da rota para interpretar corretamente o sentido.

## Arquitetura

```text
Estudante
   ↓
Telegram
   ↓ webhook HTTPS
Cloudflare Worker — Python
   ↓
Regras do BUSIVS
   ↕
Durable Object / SQLite
   ↓
Telegram Bot API
```

A arquitetura foi mantida propositalmente pequena para permanecer **gratuita ou próxima de custo zero**.

Não há:

- frontend web separado;
- banco relacional tradicional;
- GPS próprio;
- cadastro permanente de usuários.

## Tecnologias

- Python
- Cloudflare Workers para Python
- Wrangler / PyWrangler
- Durable Objects
- SQLite no Durable Object
- Telegram Bot API
- Telegram Webhooks
- python-telegram-bot na branch de testes locais
- Git e GitHub

## Organização das branches

```text
main
→ produção Cloudflare

alpha
→ testes locais por polling

local
→ versão original preservada como fallback/referência
```

O desenvolvimento funcional é validado primeiro na `alpha` antes de ser adaptado para `main`.

## Estado atual

```text
Bot Telegram                            ✅
Circular Principal                     ✅
Micro-ônibus de reforço                ✅
Localização colaborativa               ✅
Próximos horários                      ✅
Rota e sentido                         ✅
Avisos operacionais                    ✅
Painel administrativo                  ✅
Proteções de coerência                 ✅
Cloudflare Worker                      ✅ produção
Telegram Webhook                       ✅ produção
Durable Object                         ✅ produção
Execução local por polling             ✅
```

A fase funcional principal está fechada. O projeto entra agora em **melhoria contínua orientada pelo uso real**.

## Próximas melhorias possíveis

Sem aumentar complexidade sem necessidade, o BUSIVS pode evoluir com:

- proteção adicional contra spam e trotes;
- rate limit temporário por usuário/ponto;
- consolidação de muitas confirmações idênticas;
- tratamento avançado de confirmações conflitantes;
- tags NFC nos pontos;
- modo férias e horários especiais mais estruturado;
- refinamento de estimativas com dados reais;
- autenticação institucional, caso passe a ser necessária;
- métricas e estatísticas, caso gerem valor real para o serviço.

## Documentação

- [Continuidade e estado atual](CONTINUIDADE.md)
- [Fluxo do Telegram](docs/FLUXO_TELEGRAM.md)
- [Roadmap](docs/ROADMAP_BETA.md)
- [Arquitetura](docs/ARQUITETURA.md)
- [Plano de avisos](docs/PLANO_AVISOS.md)
- [Segurança pós-protótipo](docs/POS_PROTOTIPO_SEGURANCA.md)

## Autor

**Gabriel Salermo**  
Aluno de **BCET / Engenharia da Computação — UFRB**

Projeto desenvolvido a partir de uma necessidade real da comunidade acadêmica do Campus Cruz das Almas.

---

### BUSIVS BOT

> **Informação colaborativa para reduzir a incerteza de quem está esperando o circular.**
