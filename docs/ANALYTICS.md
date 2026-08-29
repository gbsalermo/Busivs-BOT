# Analytics — BUSIVS

> Implementação da Etapa 1 — Fundação de Analytics. Branch inicial: `feat/analytics-fundacao`.

## Objetivo

Criar métricas de uso reais sem permitir que analytics participe das decisões operacionais do BUSIVS.

Regra obrigatória:

```text
falha de analytics != falha do bot
```

Uma exceção durante a gravação de métrica é absorvida pela camada final. Localização, marcação, Principal, Micro, antiteleporte, engajamento, webhook e cron continuam seu fluxo normal.

---

## Arquivos

```text
cloudflare/src/analytics.py
```

Responsável apenas por persistência e agregação.

```text
cloudflare/src/entry_engajamento_final.py
```

Integra analytics na camada efetiva de produção sem alterar a cadeia inferior de regras.

```text
cloudflare/tests/test_analytics.py
```

Testes da deduplicação, separação do administrador, contagem de eventos e anonimização.

---

## Persistência

Analytics usa o mesmo Durable Object já existente, mas com chaves próprias.

Não foi criado novo binding, nova classe de Durable Object ou migração de `wrangler.jsonc`.

Chaves:

```text
analytics:schema_version
analytics:total_unique
analytics:daily:AAAA-MM-DD
analytics:user:<hash>
```

Nenhuma chave operacional de localização é reutilizada.

### Registro diário

Formato conceitual:

```json
{
  "schema": 1,
  "data": "2026-08-28",
  "usuarios": ["hash..."],
  "interacoes": 25,
  "eventos": {
    "consulta_localizacao": 12,
    "proximos_horarios": 4
  },
  "admin_interacoes": 3,
  "admin_eventos": {},
  "primeiro_evento_em": "...",
  "ultimo_evento_em": "..."
}
```

`usuarios` contém identificadores anonimizados, não Telegram IDs brutos.

---

## Privacidade

O identificador usado para deduplicação é derivado por SHA-256 e truncado para 24 caracteres.

```text
Telegram ID -> hash -> chave de analytics
```

O módulo de analytics não precisa recuperar o Telegram ID original.

Observação: outras funcionalidades operacionais do BUSIVS, como engajamento e histórico de confirmação, podem possuir identificadores próprios por necessidade funcional. A política descrita aqui vale para o novo armazenamento de analytics.

---

## Usuário único x interação

São métricas diferentes.

Exemplo:

```text
mesma pessoa consulta 10 vezes
=> 1 usuário único
=> 10 interações
```

O sistema mantém:

- usuários únicos no dia;
- usuários únicos agregados no período;
- total de usuários registrados desde a ativação do analytics;
- primeira interação do usuário;
- última interação do usuário;
- quantidade de interações do usuário.

O contador começa somente após o deploy desta versão. Ele não reconstrói retroativamente todo o histórico anterior.

---

## Administrador

Ações do administrador são mantidas separadas:

```text
admin_interacoes
admin_eventos
```

Elas não entram em:

- usuários únicos públicos;
- interações públicas;
- total registrado de usuários comuns;
- eventos públicos.

---

## Eventos iniciais

A camada final classifica as ações em eventos como:

```text
inicio
menu
consulta_localizacao
abrir_marcacao
proximos_horarios
listar_horarios
marcacao_principal
marcacao_micro
confirmacao_principal
confirmacao_micro
micro
ajuda
manual
rota
feedback
engajamento_enviado
engajamento_sim
engajamento_nao_vi
engajamento_expirado
comando_desconhecido
outra_acao
```

### Tentativa x confirmação

`marcacao_principal` e `marcacao_micro` representam a ação do usuário ao escolher um ponto.

`confirmacao_principal` e `confirmacao_micro` são eventos auxiliares gravados somente quando a chamada de registro retorna `aceito=True`.

O evento de confirmação usa `contar_interacao=False`, portanto uma única ação não infla artificialmente o total de interações.

---

## Engajamento

Analytics mede:

- convites enviados com sucesso pela API do Telegram;
- resposta `Sim, marcar ponto`;
- resposta `Não vi`;
- tentativa de responder convite expirado.

O envio automático pelo cron não é considerado uma interação do usuário.

---

## Agregação

O Durable Object expõe:

```python
resumo_analytics(dias)
```

O método agrega até 90 dias e retorna conceitualmente:

```json
{
  "dias": 7,
  "usuarios_unicos": 100,
  "interacoes": 350,
  "eventos": {},
  "total_registrado": 150,
  "admin_interacoes": 10,
  "schema": 1
}
```

Esse RPC é a base para a Etapa 2 — painel `📊 Estatísticas`.

---

## O que não foi alterado

A Etapa 1 não modifica:

- `cloudflare/wrangler.jsonc`;
- binding `BUS_STATE`;
- cron `* * * * *`;
- Telegram Webhook;
- horários;
- blocos;
- referência de volta;
- regras de RU;
- Biblioteca;
- antiteleporte;
- Principal;
- Micro;
- limite de 20 usuários dos lotes de engajamento.

---

## Testes da Etapa 1

Cobertura adicionada para:

1. mesmo usuário não duplicar usuários únicos no dia;
2. usuários diferentes incrementarem o total;
3. administrador não contaminar métrica pública;
4. evento auxiliar de confirmação não duplicar interação;
5. Telegram ID não aparecer em claro no armazenamento de analytics.

Além dos testes automatizados, antes do merge/deploy devem ser verificados os fluxos normais de localização e marcação do Principal e do Micro.

---

## Próxima etapa

Após validar e promover a fundação:

```text
ETAPA 2 — Painel administrativo de estatísticas
```

Primeiras visões previstas:

- hoje;
- últimos 7 dias;
- últimos 30 dias;
- total registrado;
- interações;
- consultas de localização;
- confirmações;
- Principal x Micro;
- efetividade inicial do engajamento.
