# CONTINUIDADE — BUSIVS BOT

Documento técnico para retomar o projeto rapidamente sem depender do histórico da conversa.

> **Atualizado em 19/08/2026.** Produção em Cloudflare Workers + Telegram. A lógica atual privilegia confirmações reais: horários identificam as voltas, mas pontos conduzem o estado dentro do bloco. Marcações temporalmente suspeitas não são bloqueadas e ficam separadas da última localização confiável até nova evidência.

---

# 1. Princípios atuais

O BUSIVS não possui GPS. Combina horários, rota, confirmações colaborativas, estimativas e avisos.

Ordem de autoridade:

```text
confirmação confiável > inferência pelo trajeto > horário
```

Regras fundamentais:

1. horário é referência da volta, não prova de posição;
2. dentro de um bloco, o relógio sozinho não encerra/inicia voltas;
3. informação suspeita deve ser sinalizada, não bloqueada;
4. indicação suspeita não pode contaminar o estado confiável;
5. janelas operacionais continuam fortes na abertura/fim dos blocos;
6. Principal e Micro possuem estados independentes.

---

# 2. Produção

```text
main  -> produção / deploy automático Cloudflare
alpha -> testes locais por polling
local -> referência/fallback histórico
```

Entrypoint atual: `cloudflare/src/entry_antiteleporte.py`.

O projeto possui camadas `entry_*`. Sempre conferir a cadeia de herança/entrypoint antes de editar lógica antiga.

Estado compartilhado: Durable Object / SQLite. Secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `ADMIN_TELEGRAM_ID`. Nunca versionar valores reais.

---

# 3. Rota conceitual

Sentido RUA:

```text
RU -> Fitotecnia -> Solos -> Pav I -> Biblioteca -> Pav II
-> Pav Engenharia (opcional) -> Portão 2 -> Alex -> Canaã -> Portão 1
```

Sentido RU:

```text
Portão 1 -> Biblioteca -> Torre/COTEC (opcional) -> RU
```

Biblioteca é ambígua porque aparece na ida e no retorno. Nunca decidir sentido apenas pelo ID `biblioteca`.

---

# 4. Horários = referência da volta

Cada volta continua conectada ao horário oficial correspondente, mas o horário não troca a volta sozinho.

Exemplo: referência 11:30; se chegar 12:00 sem evidência de RU/nova volta, continua sendo a volta de 11:30.

Isso é especialmente importante em pico/atrasos.

Horário continua forte para abertura do bloco/saída Garagem, fim operacional do bloco, lacunas entre blocos e informação de próximas referências. O encerramento do bloco continua impedindo voltas fantasmas.

---

# 5. RU = fim da volta, não começo

Confirmação **confiável** no RU significa chegada ao RU / fim da volta.

Se houver outra volta no bloco, Fitotecnia é apenas o **primeiro ponto esperado**. Não é obrigatório confirmar Fitotecnia para começar a próxima volta.

Se ninguém marcar Fitotecnia e aparecer Solos, Pav I, Biblioteca, Pav II etc., esse ponto pode evidenciar que a nova volta já começou.

Na última volta do bloco, manter o contexto de retorno/Garagem e os possíveis pontos ainda atendidos antes da Garagem.

---

# 6. Nova volta sem RU explícito

Usuários podem deixar de confirmar o RU. O sistema pode reconhecer reinício pelos pontos.

```text
última posição confiável avançada: P2/Alex/Canaã/P1
mais tarde: Fitotecnia/Solos/Pav I
=> forte evidência de volta anterior concluída + nova volta iniciada
=> associar à próxima referência oficial compatível
```

Biblioteca depois de P1 continua ambígua: pode ser retorno ou, após uma volta inteira silenciosa, uma nova ida. Nova evidência deve resolver.

---

# 7. Proteção contra marcações ruins — NÃO BLOQUEAR

Foram abandonadas as antigas travas gerais de deslocamento (tempos fixos, 1 min/ponto, 30 s/etapa etc.) porque causavam falsos bloqueios.

Hoje só alguns saltos característicos geram suspeita:

```text
Fitotecnia -> Biblioteca : < 1 min
Biblioteca -> Portão 1   : < 2 min
Portão 1 -> Biblioteca   : < 1 min
Portão 1 -> RU           : < 2 min
```

Fluxo: salto rápido -> perguntar `Você tem certeza?` -> cancelar mantém estado anterior; confirmar guarda indicação como **não confiável**.

A indicação não confiável fica ativa até surgir nova evidência. Não expira automaticamente em poucos minutos.

---

# 8. Estado confiável x indicação suspeita

Uma indicação suspeita NÃO pode encerrar volta, iniciar volta, alterar definitivamente sentido, substituir a última localização confiável, disparar retorno/Garagem ou servir de base obrigatória para o próximo registro.

`Onde está o ônibus?` deve continuar mostrando a última localização confiável como referência e avisar que existe uma indicação ainda não confirmada.

A próxima evidência resolve a situação usando a última confirmação confiável anterior.

---

# 9. Caso crítico: P1 -> RU suspeito

```text
P1 confiável -> RU rápido -> usuário confirma certeza
```

Resultado correto:

```text
P1 continua localização confiável
RU fica apenas como indicação não confiável
volta NÃO termina
```

Se depois aparecer Biblioteca, RU suspeito é desconsiderado, Biblioteca vira o foco e continua o retorno da mesma volta.

Se depois aparecer Fitotecnia/Solos/Pav I em contexto compatível, existe evidência de que a volta anterior terminou e outra começou; pode avançar para a próxima referência.

Objetivo: um voto ruim nunca deve encerrar ou impedir a volta verdadeira.

---

# 10. Evidência posterior vence suspeita

Exemplo: Biblioteca confiável -> P1 em 10 s (suspeito) -> depois Canaã plausível a partir da Biblioteca. Canaã deve prevalecer.

Regra:

```text
nova confirmação plausível > indicação suspeita pendente
```

O estado deve ser reconstruído a partir da última confirmação confiável, não da suspeita.

---

# 11. Fim de bloco e última volta

O relógio não troca voltas intermediárias, mas continua fechando o contexto operacional no fim do bloco.

Na última volta, informar objetivamente: última volta do bloco, retorno/Garagem quando aplicável, pontos ainda possíveis no retorno e próxima saída no bloco seguinte.

Chegada ao RU na última volta não necessariamente significa Garagem imediata; o circular ainda pode passar por Fitotecnia/Solos no percurso de retorno conforme a operação modelada.

---

# 12. Referência especial 20:00

Existe volta de 20:00 baseada na rotina do ano anterior: pode não ocorrer; P1 estimado ~20:10–20:15; fim ~20:25; pode passar antes. Manter aviso de que é previsão.

---

# 13. Micro

Micro é reforço e possui estado separado. Pode operar nos horários cadastrados ou esporadicamente.

A antiga pré-trava rígida de sequência/tempo do Micro foi removida. Não reintroduzir trava temporal geral sem teste real.

A ativação esporádica possui a regra de expiração operacional atualmente definida em código (30 min nos casos aplicáveis). Não exibir frases internas como `Operação confirmada há X min` na localização do usuário.

Admin possui `🛠️ Ajuste manual` para escolher referência, corrigir ponto/sentido, corrigir Micro e Garagem/encerrar bloco.

---

# 14. Pedidos colaborativos de confirmação

Quando há silêncio após consultas, existe fluxo para pedir evidência aos usuários recentes.

- pelo menos 10 candidatos por disparo;
- normal: primeiro pedido após ~5 min sem nova confirmação;
- pico: ~10 min;
- segundo disparo aproximadamente 15/20 min;
- máximo 2 avisos por volta;
- nova confirmação zera/cancela o fluxo;
- candidatos podem entrar até ~1 min antes do envio;
- autor da última confirmação pode receber pergunta intermediária ~7/8 min quando aplicável;
- fluxos não se sobrepõem;
- resposta direta ao aviso disponível por 3 min.

Objetivo: pedir confirmação quando falta informação, não exigir confirmação a cada dois pontos.

---

# 15. Interface

Evitar expor regras internas, limites de validade e detalhes do algoritmo. Mostrar conclusão operacional simples.

Controles administrativos ficam em `Ajuste manual`, não em `Onde está o ônibus?`.

---

# 16. Arquivos sensíveis

```text
entry_antiteleporte.py -> suspeitas, confirmação/cancelamento, estado confiável x indicação fraca, RU
expiracao_volta.py     -> horários como referência e encerramento de bloco
estado_bus_core.py     -> persistência Principal/Micro
regras*.py             -> localização/sentido/mensagens
dados.py               -> horários/pontos
entry_admin_hub.py     -> interface / Ajuste manual
```

---

# 17. Testes prioritários

```text
1. P1 confiável -> RU rápido -> confirmar
   P1 continua confiável; RU só incerto.
2. P1 -> RU suspeito -> Biblioteca
   RU descartado; Biblioteca assume; volta ainda não acabou.
3. P1 -> RU suspeito -> Fitotecnia/Solos/Pav I
   reconhecer nova volta quando compatível.
4. Biblioteca -> P1 <2 min
   perguntar certeza; nunca bloquear definitivamente.
5. Biblioteca -> P1 suspeito -> Canaã plausível
   Canaã prevalece.
6. volta 11:30 atravessa 11:55/12:00 sem nova evidência
   continua referência 11:30.
7. RU confiável com outra volta no bloco
   fim da volta; Fitotecnia apenas primeiro esperado.
8. RU -> primeira evidência nova em Solos/Pav I/P2
   aceitar nova volta sem exigir Fitotecnia.
9. última volta do bloco
   retorno/Garagem + próxima saída correta.
10. Micro
    sem bloqueio temporal geral antigo.
```

---

# 18. Histórico da reformulação de 19/08/2026

As tentativas anteriores de anti-teletransporte passaram por mínimos fixos, mínimos por ponto, 30 segundos por etapa e segunda tentativa. Causaram falsos bloqueios e foram abandonadas.

Decisão atual: **não bloquear**. Poucos saltos característicos geram hipótese não confiável e evidência posterior resolve.

Commits importantes:

```text
511e6aa -> início da reformulação
3090718 -> confirmação suspeita sem bloqueio
2618931 -> horários intermediários deixam de expirar a volta
0f9bedd -> indicação suspeita separada do estado confiável, especialmente RU
```

---

# 19. Regras que não devem ser quebradas

1. Confirmação confiável > inferência > horário.
2. Horário identifica a volta, mas não a troca sozinho dentro do bloco.
3. RU confiável encerra volta; não inicia automaticamente outra.
4. Fitotecnia é esperado, não obrigatório.
5. Outro ponto plausível pode provar nova volta.
6. Biblioteca sempre exige contexto.
7. Suspeita nunca bloqueia confirmação correta posterior.
8. Suspeita nunca encerra/inicia volta sozinha.
9. Estado confiável e suspeita ficam separados.
10. Não reintroduzir trava geral de tempo.
11. Horário continua forte na abertura/fim de bloco.
12. Principal e Micro permanecem independentes.
13. Usuário não precisa conhecer regras internas.
14. Última volta deve deixar claro que não há saída imediatamente em seguida.
15. Não versionar secrets/IDs administrativos.

---

# 20. Próximo foco

Observar a lógica nova em voltas reais. O principal risco agora é resolver ambiguidades entre retorno e nova volta quando faltam confirmações intermediárias.

Quando surgir caso inesperado, registrar a sequência real de **horários + pontos** e ajustar a inferência sem transformar horário em GPS nem criar bloqueios gerais.
