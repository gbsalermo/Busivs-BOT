# Fluxo do Telegram — BUSIVS BOT

> UX efetiva da produção Cloudflare em 31/08/2026. Este arquivo substitui o fluxo inicial do protótipo que previa autenticação institucional e NFC.

## 1. Princípio de interface

A experiência principal é feita por **botões inline**. Comandos são secundários e não devem ser documentados como existentes sem conferir os handlers atuais.

O ponto de entrada seguro é `/start`, que abre o menu.

---

## 2. Primeiro acesso / menu

```text
/start
  ↓
👋 Bem-vindo ao BUSIVS!
  ↓
🚌 BUSIVS BOT
Escolha uma opção:

[ 🚌 Onde está o ônibus? ]
[ 📍 Informar ponto atual ]      <- apenas quando há operação disponível
[ ⏰ Próximos horários ]
[ 📋 Listar horários ]
[ 🚐 Confirmar que o micro está rodando ]
[ ❓ Ajuda ]
```

Quando o Micro já está ativo, o botão muda para indicar que ele está em operação.

Usuário comum não precisa validar e-mail institucional para consultar ou registrar ponto no fluxo atual.

---

## 3. Onde está o ônibus?

```text
🚌 Onde está o ônibus?
        ↓
CIRCULAR PRINCIPAL
+ última confirmação/estado confiável
+ sentido/próximo ponto quando aplicável
+ referência da volta
+ contexto de retorno/Garagem quando aplicável
```

Se o Micro estiver ativo, a mesma resposta inclui uma seção separada:

```text
────────────
🚐 MICRO — REFORÇO
```

Principal e Micro nunca devem compartilhar o mesmo estado de localização.

A resposta também pode incluir impacto de avisos operacionais ativos, como atraso, chuva, quebra, portão fechado ou rota temporariamente alterada.

Após a consulta, usuário comum pode se tornar candidato ao mecanismo de engajamento colaborativo enquanto o bloco estiver ativo.

---

## 4. Informar ponto atual

O botão só aparece quando existe operação do Principal e/ou Micro disponível.

### Apenas Principal ativo

```text
📍 Informar ponto atual
        ↓
Onde o circular principal acabou de passar?
        ↓
[ pontos da rota ]
```

### Apenas Micro ativo

```text
📍 Informar ponto atual
        ↓
Onde o micro acabou de passar?
        ↓
[ pontos da rota ]
```

### Principal + Micro ativos

```text
📍 Informar ponto atual
        ↓
📍 Qual veículo você viu?

[ 🚌 Circular principal ]
[ 🚐 Micro — reforço ]
        ↓
[ pontos da rota ]
```

A confirmação deve ser usada somente quando o usuário realmente viu o veículo passar.

Fora de uma janela operacional válida, o backend também deve rejeitar tentativa antiga/direta de registro.

---

## 5. Saltos suspeitos

Quando uma marcação representa salto temporal muito característico, o fluxo pode pedir confirmação adicional.

```text
ponto suspeito
  ↓
Você tem certeza?
  ├─ cancelar -> mantém estado confiável anterior
  └─ confirmar -> salva indicação NÃO CONFIÁVEL
```

A indicação não confiável não substitui a última localização confiável e não abre/fecha volta.

---

## 6. Micro-ônibus

Quando ainda não está ativo:

```text
[ 🚐 Confirmar que o micro está rodando ]
        ↓
[ ✅ Sim, está rodando ]
[ ❌ Voltar ]
```

A ativação representa evidência de que o Micro está operando; ela não prova sua posição física.

Depois de ativo, Principal e Micro continuam independentes e o usuário pode marcar pontos específicos do Micro.

---

## 7. Próximos horários

```text
[ ⏰ Próximos horários ]
```

Mostra as próximas referências do Circular Principal conforme a rotina cadastrada e, quando aplicável, informações do Micro.

Horário continua sendo referência operacional, não posição automática.

---

## 8. Listar horários

```text
[ 📋 Listar horários ]
        ↓
[ 🌅 Manhã ] [ 🍽️ Almoço ]
[ 🌤️ Tarde ] [ 🌙 Noite ]
```

A fonte oficial das referências é:

```text
cloudflare/src/dados.py
```

A referência das 20:00 deve aparecer como **experimental**, pois pode não ocorrer.

---

## 9. Ajuda

```text
[ ❓ Ajuda ]
        ↓
[ 🗺️ Rota atual ]
[ 📖 Dicas para uso do BOT ]
[ 💬 Enviar feedback ]
[ ⬅️ Voltar ao menu ]
```

### Feedback

```text
💬 Enviar feedback
        ↓
Bot solicita resposta em texto
        ↓
Usuário responde
        ↓
Feedback é encaminhado ao administrador
        ↓
✅ confirmação ao usuário
```

O feedback simples já está em produção. Categorização estruturada pertence à Etapa 6 do roadmap.

---

## 10. Engajamento colaborativo proativo

Quando uma volta fica sem confirmação por tempo suficiente, usuários comuns que consultaram `Onde está o ônibus?` podem receber:

```text
🚌 Você viu o circular recentemente?

A localização está há alguns minutos sem nova confirmação.

[ 📍 Sim, marcar ponto ]
[ ❌ Não vi ]
```

Regras principais:

- convite válido por 3 minutos;
- até 20 usuários por lote em produção;
- máximo de 2 lotes coletivos por volta;
- tempos maiores em horário de pico;
- nova confirmação confiável reinicia a lacuna.

Se o convite expirar, o usuário deve voltar ao menu para registrar normalmente.

O fluxo foi corrigido em código em 25/08/2026 após o entrypoint do Worker ser ajustado para `entry_engajamento_final.py`; ainda existe um gate de validação controlada/regressão antes de Analytics.

---

## 11. Administração

O administrador recebe opções adicionais sem poluir o menu dos demais usuários.

### Referência de volta

```text
[ 🧭 Escolher volta de referência ]
        ↓
referências oficiais do bloco atual
        ↓
admin escolhe explicitamente a referência correta
```

Não usar o conceito antigo de apenas “retornar à volta anterior”.

### Garagem

```text
[ 🅿️ Garagem / Encerrar bloco ]
        ↓
marca encerramento administrativo do bloco
```

### Avisos

```text
[ 📢 Avisos ]
        ↓
avisos predefinidos
+ aviso personalizado
+ remover aviso
+ limpar avisos
```

### Outros controles

As camadas finais também possuem ajustes administrativos de ponto/sentido e Micro. Antes de alterar esses fluxos, conferir `entry_admin_hub.py`, `entry_micro_admin.py` e arquivos relacionados.

---

## 12. O que NÃO está implementado em produção

Os itens abaixo apareceram no desenho inicial do protótipo, mas não fazem parte do fluxo atual:

```text
❌ autenticação obrigatória por e-mail institucional
❌ envio/validação de código por e-mail
❌ NFC/deep link por ponto como mecanismo oficial
❌ modo de férias automático
```

Eles não devem ser implementados apenas porque aparecem no histórico do Git. Qualquer retomada exige nova decisão e inclusão explícita no plano oficial.

---

## 13. Regra de documentação

Ao atualizar este arquivo, confronte sempre o fluxo com:

```text
cloudflare/src/entry_engajamento_final.py
cloudflare/src/entry_consistencia.py
cloudflare/src/entry_admin_hub.py
cloudflare/src/entry.py
cloudflare/src/entry_core.py
```

A cadeia Cloudflare é a referência de produção; a antiga interface em `src/` é histórica/local.
