# Plano de Evolução — BUSIVS BOT

> Roadmap oficial do projeto. Revisado em 31/08/2026. O Dossiê Mestre define o que o sistema é e quais regras não podem ser quebradas; este arquivo define a ordem de evolução.

## Estado geral

```text
ETAPA 0 — concluída
GATE OPERACIONAL — pendente
ETAPA 1 — não iniciada
ETAPAS 2–8 — planejadas
```

Não criar um roadmap paralelo nem renumerar as etapas sem decisão explícita.

---

## ETAPA 0 — Limpeza da Casa + Dossiê Mestre

**Status: CONCLUÍDA e incorporada à `main`.**

Entregas:

- arquitetura real de produção mapeada;
- separação entre produção Cloudflare e base histórica/local;
- Dossiê Mestre criado;
- README e Continuidade reconciliados;
- roadmap Beta arquivado como histórico;
- política de limpeza das camadas `entry_*` definida;
- `.gitignore` ampliado;
- limite efetivo de engajamento de até 20 usuários documentado;
- auditoria da Etapa 0 registrada.

Dívida técnica mantida propositalmente:

```text
.venv já versionada
```

A remoção deve ocorrer em operação Git dedicada.

---

# GATE OPERACIONAL — Engajamento proativo

**Status: PENDENTE DE VALIDAÇÃO.**

Este gate não cria uma nova etapa do roadmap. Ele existe para impedir que uma função operacional já aprovada fique sem validação antes da evolução de Analytics.

Contexto:

Em 25/08/2026 foi relatado que os pedidos colaborativos não chegavam. O Worker ainda apontava para `entry_consistencia.py`; depois das correções, `cloudflare/wrangler.jsonc` passou a expor `entry_engajamento_final.py`.

Correções relevantes:

```text
66ce4f3 — reintegra avisos colaborativos ao entrypoint final
020f09c — ativa entry_engajamento_final.py no Worker
2a14042 — eleva lote efetivo para até 20 usuários
```

Antes de iniciar a Etapa 1, validar:

1. consulta de usuário comum gera candidatura;
2. cron a cada minuto encontra candidatos quando a lacuna atende a regra;
3. primeiro lote chega no tempo esperado;
4. segundo lote/fallback respeitam limites;
5. `Sim, marcar ponto` abre o fluxo correto;
6. `Não vi` é consumido uma vez;
7. convite expira em 3 minutos;
8. nova confirmação confiável reinicia a lacuna;
9. máximo de 2 lotes coletivos por volta permanece preservado;
10. criar teste de regressão para o comportamento essencial do cron/engajamento.

Se houver falha real, corrigir e revalidar antes de Analytics.

---

## ETAPA 1 — Fundação de Analytics

**Status: NÃO INICIADA.**

Objetivo: criar observabilidade própria do produto sem depender apenas do painel da Cloudflare.

Implementar:

- usuários únicos;
- primeira interação;
- última interação;
- total de interações;
- eventos mínimos de uso;
- separação entre usuário único e quantidade de ações;
- coleta tolerante a falhas.

Eventos iniciais sugeridos:

```text
onde_principal
onde_micro
horarios
listar_horarios
marcar_ponto_principal
marcar_ponto_micro
confirmar_micro
resposta_convite_sim
resposta_convite_nao
feedback
```

### Regra de arquitetura

Analytics deve ser observacional:

```text
try registrar métrica
catch/falha -> fluxo normal continua
```

Falha de métrica nunca pode impedir menu, consulta, confirmação, callback ou resposta do Telegram.

### Persistência

Antes de criar novas tabelas/chaves no Durable Object, documentar o formato e preservar compatibilidade com o storage existente.

### Critério de conclusão

- métricas básicas persistidas;
- nenhum fluxo funcional depende do sucesso do analytics;
- testes provam tolerância a falha;
- Dossiê/Continuidade atualizados.

---

## ETAPA 2 — Painel Administrativo de Estatísticas

Adicionar `📊 Estatísticas` somente para administração.

Exibir inicialmente:

- usuários únicos hoje;
- últimos 7 dias;
- últimos 30 dias;
- total registrado;
- interações por período;
- consultas de localização;
- confirmações;
- Principal x Micro.

Não expor dados pessoais desnecessários ao painel.

---

## ETAPA 3 — Saúde das Voltas

Medir por volta/bloco:

- quantidade de consultas;
- confirmações confiáveis;
- tempo sem confirmação;
- tempo médio entre confirmações;
- quantidade de inferências;
- pedidos automáticos de ajuda;
- horários com muita demanda e pouca colaboração.

Objetivo: identificar onde o BUSIVS é mais necessário e onde a informação é mais frágil.

---

## ETAPA 4 — Efetividade dos Avisos Colaborativos

Medir:

- pessoas convidadas por lote;
- `Sim, marcar ponto`;
- `Não vi`;
- convites expirados;
- confirmação efetivamente gerada após aviso;
- taxa de resposta em pico x horário normal;
- desempenho do limite de até 20 candidatos;
- primeiro lote x segundo lote x fallback do último autor.

Objetivo: saber se o mecanismo recupera informação ou apenas gera mensagens.

A Etapa 4 mede o mecanismo; o gate anterior à Etapa 1 apenas garante que ele está funcional.

---

## ETAPA 5 — Impacto da Colaboração

Criar métrica aproximada de consultas ajudadas por cada confirmação confiável.

Possível retorno ao usuário:

```text
📍 Obrigado!
Sua confirmação ajudou X consultas ao BUSIVS.
```

Não criar ranking público inicialmente. O objetivo é reforçar utilidade, não incentivar marcações artificiais.

---

## ETAPA 6 — Feedback Estruturado

O envio simples de feedback já existe em produção pela área de Ajuda.

Evoluir para categorias:

- localização incorreta;
- horário incorreto;
- problema no bot;
- sugestão;
- outro.

Adicionar consulta administrativa de feedbacks recentes e usar os dados para priorização.

---

## ETAPA 7 — Comunicação Operacional

Evoluir os avisos administrativos já existentes para uma central operacional simples.

Exemplos:

- circular não saiu;
- atraso informado;
- mudança temporária de rota;
- Micro indisponível;
- quebra durante o trajeto;
- operação excepcional.

Todo aviso deve ter validade/expiração para evitar informação antiga ativa.

---

## ETAPA 8 — Automação Física / Modelo Híbrido

**Direção conceitual atual:** dispositivo embarcado de baixo custo no ônibus, alimentado no próprio veículo.

Combinação preferida:

```text
ESP32
+ GPS
+ Wi-Fi institucional
+ geofences/pontos conhecidos
```

Hipótese principal:

```text
GPS entra no raio do ponto
+ conexão com uma rede institucional conhecida
=> evidência automática mais forte da presença do ônibus
```

A solução deve considerar múltiplas redes institucionais configuradas e evitar qualquer credencial real no repositório.

Rastreadores veiculares comerciais foram considerados como alternativa, mas a direção atual favorece ESP32/GPS/Wi-Fi por permitir integração direta com o modelo de confiança do BUSIVS.

Modelo desejado:

```text
evidência automática
+ confirmação colaborativa
+ inferência de rota
```

O dispositivo complementa o modelo humano; não elimina imediatamente a colaboração.

### Subetapas futuras sugeridas dentro da Etapa 8

1. prova de alimentação e conectividade no veículo;
2. leitura GPS estável;
3. reconhecimento de redes institucionais sem expor segredos;
4. geofences dos pontos prioritários;
5. envio de eventos automáticos para ambiente de teste;
6. política de confiança automática x colaborativa;
7. piloto em um veículo;
8. validação de falsos positivos/negativos antes de usar como fonte de produção.

---

# Regras para todas as etapas

1. não avançar etapa funcional sem validar a anterior;
2. mudanças de regra de negócio precisam ser documentadas no Dossiê Mestre;
3. mudança de entrypoint/Cloudflare exige revisão explícita do `wrangler.jsonc`;
4. migração de storage do Durable Object exige compatibilidade com estado existente;
5. analytics e funcionalidades auxiliares nunca podem impedir resposta do bot;
6. `main` permanece produção; mudanças de risco devem nascer em branch;
7. antes de remover camada `entry_*`, criar cobertura de regressão do comportamento fornecido;
8. `cloudflare/` é a referência de produção; `src/` não deve ser tratado como equivalente;
9. horários, pontos e blocos devem ser conferidos em `cloudflare/src/dados.py` antes de documentação/alteração;
10. decisões antigas de protótipo não voltam automaticamente ao roadmap atual.
