# Plano de Evolução — BUSIVS BOT

> Documento de etapas futuras. Não substitui o Dossiê Mestre. O Dossiê define o que o sistema é e quais regras não podem ser quebradas; este arquivo define o que será feito a seguir.

## ETAPA 0 — Limpeza da Casa + Dossiê Mestre

**Status:** em execução na branch `chore/etapa-0-limpeza-dossie`.

Objetivos:

- mapear a arquitetura real de produção;
- separar camada externa Cloudflare da cadeia interna Python;
- identificar documentação obsoleta;
- identificar código legado sem removê-lo de forma precipitada;
- reforçar `.gitignore` e organização do repositório;
- criar o Dossiê Mestre;
- estabelecer testes mínimos antes de futuras refatorações;
- reconciliar `README.md`, `CONTINUIDADE.md` e documentação técnica.

Entregas:

- `docs/DOSSIE_MESTRE_BUSIVS.md`;
- `docs/ARQUITETURA.md` atualizado;
- `.gitignore` ampliado;
- inventário das inconsistências encontradas;
- política de limpeza segura das camadas `entry_*`.

Critério de conclusão:

- documentação aponta para o entrypoint real de produção;
- regras de negócio críticas estão registradas;
- nenhuma regra operacional foi alterada apenas por refatoração;
- divergências conhecidas estão explícitas;
- branch está pronta para validação antes de qualquer merge em `main`.

---

## ETAPA 1 — Fundação de Analytics

Objetivo: criar observabilidade própria do produto sem depender do painel da Cloudflare.

Implementar:

- usuários únicos;
- primeira interação;
- última interação;
- total de interações;
- eventos mínimos de uso;
- separação entre usuário único e quantidade de ações;
- coleta tolerante a falhas: analytics nunca pode bloquear o bot.

Eventos iniciais sugeridos:

```text
onde_principal
onde_micro
horarios
listar_horarios
marcar_ponto_principal
marcar_ponto_micro
resposta_convite_sim
resposta_convite_nao
feedback
```

---

## ETAPA 2 — Painel Administrativo de Estatísticas

Adicionar `📊 Estatísticas` somente para administração.

Exibir:

- usuários únicos hoje;
- últimos 7 dias;
- últimos 30 dias;
- total registrado;
- interações por período;
- consultas de localização;
- confirmações;
- Principal x Micro.

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
- desempenho do limite de até 20 candidatos.

Objetivo: saber se o mecanismo de engajamento recupera informação ou apenas gera mensagens.

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

Categorias iniciais:

- localização incorreta;
- horário incorreto;
- problema no bot;
- sugestão;
- outro.

Permitir consulta administrativa dos feedbacks recentes e usar os dados para priorização.

---

## ETAPA 7 — Comunicação Operacional

Evoluir avisos administrativos para uma central operacional simples.

Exemplos:

- circular não saiu;
- atraso informado;
- mudança temporária de rota;
- Micro indisponível;
- operação excepcional.

Todo aviso deve ter validade/expiração para evitar informação antiga ativa.

---

## ETAPA 8 — Automação Física / Modelo Híbrido

Prototipar dispositivo embarcado com ESP32 e uma ou mais fontes:

- Wi‑Fi institucional;
- GPS;
- identificação por pontos conhecidos.

Modelo desejado:

```text
evidência automática
+ confirmação colaborativa
+ inferência de rota
```

O dispositivo complementa o modelo humano; não elimina imediatamente a colaboração.

---

# Regras para todas as etapas

1. não avançar etapa funcional sem validar a anterior;
2. mudanças de regra de negócio precisam ser documentadas no Dossiê Mestre;
3. mudança de entrypoint/Cloudflare exige revisão explícita do `wrangler.jsonc`;
4. migração de storage do Durable Object exige compatibilidade com estado existente;
5. analytics e funcionalidades auxiliares nunca podem impedir resposta do bot;
6. `main` permanece produção; alterações de risco devem nascer em branch;
7. antes de remover camada `entry_*`, criar cobertura de regressão do comportamento que ela fornece.
