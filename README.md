# BUSIVS BOT 🚌

Bot comunitário desenvolvido para auxiliar estudantes da **UFRB — Campus Cruz das Almas** a consultar horários do circular e acompanhar sua situação de forma simples e colaborativa pelo Telegram.

> **Status:** versão funcional hospedada em produção com Cloudflare Workers e Telegram Webhook.

## Sobre o projeto

O BUSIVS BOT nasceu de um problema cotidiano: quem depende do circular nem sempre sabe se o ônibus já passou, está atrasado, está retornando ou quando acontecerá a próxima saída.

Em vez de exigir GPS ou um aplicativo próprio, o sistema combina **horários oficiais**, **regras da rota** e **confirmações colaborativas dos estudantes** para reduzir essa incerteza.

O projeto foi desenvolvido por **Gabriel Salermo**, aluno do **Bacharelado Interdisciplinar em Ciências Exatas e Tecnológicas (BCET) / Engenharia da Computação da UFRB**.

## O que o sistema faz

Pelo Telegram, o usuário pode:

- consultar os próximos horários do circular;
- listar horários por período do dia;
- consultar a rota principal;
- informar em qual ponto o ônibus acabou de passar;
- consultar a última localização confirmada;
- obter estimativa de sentido e próximo ponto;
- identificar situações de ida, retorno, espera e pré-saída;
- visualizar previsões aproximadas de chegada ao Portão 1;
- receber indicação experimental de possível atraso;
- colaborar com outros estudantes sem instalar um aplicativo adicional.

O sistema diferencia explicitamente **confirmação real** de **estimativa baseada no horário**.

## Interface

O Telegram é a interface do BUSIVS.

![Interface inicial do BUSIVS BOT](docs/images/interface-inicial.png)

```text
🚌 Onde está o ônibus?
📍 Informar passagem
⏰ Próximos horários
📋 Listar horários
🗺️ Rota atual
📢 Avisos
```

## Localização colaborativa

Quando um estudante vê o ônibus passar, pode selecionar o ponto correspondente. Essa confirmação alimenta um estado operacional compartilhado e temporário.

A partir da sequência de pontos, o BUSIVS consegue estimar o movimento do ônibus, o sentido e o próximo ponto esperado. A lógica também considera pontos que aparecem mais de uma vez na rota, como a Biblioteca, e permite pontos opcionais.

Para reduzir informações incorretas, o serviço possui proteções contra registros duplicados, passagens fora do período de circulação e deslocamentos fisicamente improváveis em intervalos muito curtos. O histórico é curto e operacional: o objetivo não é rastrear usuários nem manter um histórico permanente de localização.

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

## Arquitetura em produção

```text
Estudante
   ↓
Telegram
   ↓ webhook HTTPS
Cloudflare Worker (Python)
   ↓
Regras do BUSIVS
   ↕
Durable Object / SQLite
   ↓
Telegram Bot API
```

A hospedagem foi desenhada para permanecer **gratuita ou próxima de custo zero**. O Cloudflare Worker recebe os updates do Telegram por webhook, enquanto um Durable Object mantém apenas o estado compartilhado necessário para acompanhar a volta atual.

A versão original em polling foi preservada como referência e fallback do projeto.

## Tecnologias

- Python
- Cloudflare Workers para Python
- Wrangler / PyWrangler
- Durable Objects com armazenamento SQLite
- Telegram Bot API e Webhooks
- JSON para horários, pontos e definição da rota
- Git e GitHub

Secrets como token do bot e segredo do webhook são mantidos no ambiente da Cloudflare e não versionados no repositório.

## Decisões de projeto

O BUSIVS foi mantido propositalmente pequeno. Não há banco relacional tradicional, frontend separado ou GPS próprio. Informações permanentes da operação ficam em estruturas simples; o estado da localização é temporário e compartilhado pelo Durable Object.

Horários são referência, não prova da posição real. Uma confirmação colaborativa tem prioridade quando válida, mas o sistema aplica regras de coerência para evitar que uma sequência impossível distorça a localização mostrada aos demais estudantes.

## Estado atual

```text
Bot e interface Telegram                    ✅
Horários do Circular Principal              ✅
Rota / sentido / próximo ponto              ✅
Localização colaborativa                    ✅
Ciclo operacional e expiração de estado     ✅
Proteções de coerência das confirmações      ✅
Cloudflare Worker                            ✅ produção
Webhook Telegram                             ✅ produção
Durable Object                               ✅ produção
Secrets de produção                         ✅ configurados
Observabilidade / logs                       ✅ habilitável na Cloudflare
```

O projeto entra agora em uma fase de **melhoria contínua do serviço em produção**: problemas observados no uso real serão corrigidos incrementalmente, priorizando eficiência, confiabilidade e simplicidade.

## Futuras melhorias

Após a consolidação do serviço atual, o BUSIVS pode evoluir com:

- avisos, comunicados e ocorrências operacionais;
- suporte ao Micro-ônibus além do Circular Principal;
- tags NFC nos pontos para facilitar confirmações;
- tratamento de desvios e alterações de acesso aos portões;
- modo específico para férias e períodos sem aula;
- refinamento das estimativas com dados obtidos durante o uso real;
- mecanismos adicionais contra informações incorretas ou abuso;
- avisos e alertas automáticos para situações relevantes;
- autenticação institucional, caso o uso real demonstre necessidade;
- métricas e estatísticas operacionais, caso passem a gerar valor para o serviço.

Essas melhorias fazem parte do **pós-protótipo** e não são requisito para considerar a versão atual funcional.

## Documentação técnica

- [Continuidade e estado atual](CONTINUIDADE.md)
- [Fluxo do Telegram](docs/FLUXO_TELEGRAM.md)
- [Roadmap até Beta](docs/ROADMAP_BETA.md)
- [Arquitetura](docs/ARQUITETURA.md)

## Autor

**Gabriel Salermo**  
Aluno de **BCET / Engenharia da Computação — UFRB**

---

### BUSIVS BOT

> **Colaboração e informação para diminuir a incerteza de quem está esperando o circular.**
