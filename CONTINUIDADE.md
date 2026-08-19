# CONTINUIDADE — BUSIVS BOT

Documento técnico para retomar o projeto rapidamente sem depender do histórico da conversa.

> **Atualizado em 19/08/2026 após pente-fino de consistência.** Produção em Cloudflare Workers + Telegram. Principal e Micro agora seguem o mesmo princípio: horários identificam referências operacionais, mas os pontos colaborativos conduzem a posição e a troca de volta. Marcações temporalmente suspeitas não são bloqueadas e ficam separadas da última localização confiável até nova evidência.

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
6. Principal e Micro possuem estados independentes, mas seguem a mesma filosofia colaborativa.

---

# 2. Produção

```text
main  -> produção / deploy automático Cloudflare
alpha -> testes locais por polling
local -> referência/fallback histórico
```

Entrypoint atual:

```text
cloudflare/src/entry_consistencia.py
```

Cadeia final relevante:

```text
entry_consistencia.py
-> entry_antiteleporte.py
-> entry_admin_hub.py
-> demais camadas entry_*
```

O projeto possui várias camadas `entry_*`. Sempre conferir o entrypoint do `wrangler.jsonc` e a cadeia de herança antes de alterar uma camada antiga.

Estado compartilhado: Durable Object / SQLite.

Secrets:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
ADMIN_TELEGRAM_ID
```

Nunca versionar valores reais.

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

# 4. Horários = referência, não gatilho de troca

Cada volta pode continuar ligada a uma referência oficial, mas o horário não troca a volta sozinho.

Exemplo:

```text
referência 11:30
12:00 sem evidência de RU/nova volta
=> continua sendo a volta de 11:30
```

O código antigo ainda possuía uma inferência de `próxima volta provavelmente em andamento` baseada apenas no relógio. Essa inconsistência foi removida de `volta_referencia.py`.

Agora:

```text
referência só muda por evidência de pontos,
ajuste administrativo,
ou fechamento/abertura de bloco.
```

Horário continua forte para abertura do bloco/saída Garagem, fim operacional do bloco, lacunas entre blocos e informação de próximas referências oficiais.

---

# 5. RU = fim da volta, não começo

Confirmação **confiável** no RU significa:

```text
chegada ao RU / fim da volta
```

RU não inicia automaticamente a próxima volta.

Se houver outra volta no bloco, Fitotecnia é apenas o **primeiro ponto esperado**. Não é obrigatório confirmar Fitotecnia.

Se ninguém marcar Fitotecnia e a primeira nova evidência vier em Solos, Pav I, Biblioteca, Pav II etc., ela pode comprovar que a nova volta já começou.

Na última volta do bloco, manter o contexto de retorno/Garagem; Fitotecnia/Solos podem pertencer ao trajeto para a Garagem, portanto não inventar nova volta depois da última referência oficial do bloco.

---

# 6. Nova volta sem RU explícito

Usuários podem deixar de marcar o RU. O sistema deve reconhecer reinício pelos pontos.

```text
última posição confiável já no retorno
-> depois aparece Fitotecnia/Solos/Pav I
=> forte evidência de volta anterior concluída + nova volta iniciada
```

Quando existe uma próxima referência dentro do mesmo bloco, ela pode ser associada à nova volta.

A troca nunca ocorre simplesmente porque chegou o horário da próxima saída.

Biblioteca depois de P1 continua sendo coerente com o retorno da mesma volta e não deve abrir uma nova volta sozinha.

---

# 7. Proteção contra marcações ruins — NÃO BLOQUEAR

Não existe mais trava geral de tempo entre pontos.

As abordagens antigas de mínimos fixos, tempo por ponto, 30 s/etapa e segunda tentativa foram abandonadas porque causavam falsos bloqueios.

Somente alguns saltos muito característicos geram confirmação adicional:

```text
Fitotecnia -> Biblioteca : < 1 min
Biblioteca -> Portão 1   : < 2 min
Portão 1 -> Biblioteca   : < 1 min
Portão 1 -> RU           : < 2 min
```

Essas mesmas regras valem para **Principal e Micro**.

Fluxo:

```text
salto rápido
-> "Você tem certeza?"
-> cancelar: mantém estado anterior
-> confirmar: salva apenas como indicação NÃO CONFIÁVEL
```

Nunca bloquear definitivamente o ponto.

---

# 8. Estado confiável x indicação suspeita

Principal e Micro mantêm a indicação suspeita separada do estado confiável.

Uma indicação suspeita NÃO pode:

- encerrar volta;
- iniciar volta;
- alterar definitivamente sentido;
- substituir a última localização confiável;
- disparar retorno/Garagem;
- virar base obrigatória para o próximo registro.

Ela permanece até surgir nova evidência.

`Onde está o ônibus?` deve mostrar a localização confiável e, separadamente, avisar que existe uma indicação ainda não confirmada.

---

# 9. Evidência posterior vence suspeita

Exemplo:

```text
Biblioteca confiável
-> P1 em poucos segundos = suspeito
-> depois Canaã plausível a partir da Biblioteca
```

Resultado:

```text
Canaã prevalece
P1 suspeito é descartado
```

Outro caso:

```text
P1 confiável
-> RU rápido = suspeito
-> usuário insiste
-> depois Biblioteca
```

Resultado:

```text
RU suspeito não encerra a volta
Biblioteca assume o foco do retorno
```

Se depois do RU suspeito aparecer Fitotecnia/Solos/Pav I em contexto compatível, pode existir evidência de nova volta.

---

# 10. Registro colaborativo independente de horário

Foi criado:

```text
cloudflare/src/registro_colaborativo.py
```

Ele registra pontos usando somente:

- rota;
- histórico confiável da volta atual;
- sequência dos pontos;
- evidência de reinício.

Ele não consulta a grade horária do Principal para decidir se o ponto é válido.

Isso foi necessário principalmente para o Micro, porque a implementação anterior reutilizava `registrar_passagem()` do Principal e podia sofrer efeitos colaterais de janelas/lacunas do Circular Principal.

---

# 11. Micro — mesmas regras novas do Principal

O Micro agora usa a mesma filosofia colaborativa:

1. ponto real conduz o estado;
2. relógio não troca volta;
3. RU confiável encerra a volta;
4. nova volta é reconhecida por nova evidência de rota;
5. Biblioteca sem contexto suficiente fica ambígua;
6. marcação suspeita vira indicação não confiável;
7. suspeita nunca bloqueia confirmação posterior;
8. não usa a grade do Principal para validar seus pontos.

Foi removido do caminho efetivo o comportamento antigo de decidir `Biblioteca = retorno` apenas porque haviam passado 15 minutos. Esse tipo de regra temporal não deve voltar.

---

# 12. Referência do Micro

Horários oficiais atuais do Micro:

```text
07:25 — Garagem
07:40 — RU/Residências
07:55 — RU/Residências

11:20 — Garagem
11:55 — RU/Residências
12:20 — RU/Residências
```

A alteração de 11:30 para **11:20** foi deliberada e registrada anteriormente no commit `5623381`.

Quando o Micro é ativado perto de uma saída oficial, sua sessão pode ser associada a essa referência.

A referência seguinte só avança quando os **pontos** comprovam uma nova volta. Não avança pelo relógio.

O sistema também não deve saltar automaticamente do último horário da manhã para o bloco do almoço.

Se o Micro continuar rodando sem uma próxima referência dentro do mesmo bloco, a operação passa a ser tratada como **esporádica**, sem vínculo obrigatório com outra saída oficial distante.

---

# 13. Ativação e expiração do Micro

Usuário comum pode confirmar operação apenas dentro da faixa funcional ampliada.

Regra atual:

```text
início da faixa = 30 min antes da primeira referência oficial
fim da faixa    = 13:00
```

Dentro dessa faixa, a ativação normal permanece válida até o fim da faixa funcional, salvo desativação administrativa.

O `30 min` de expiração aplica-se ao **override administrativo fora da faixa funcional**, para evitar uma sessão extraordinária esquecida indefinidamente.

Portanto, não confundir:

```text
30 min antes da primeira saída = antecedência para ativação comum
30 min de duração              = somente override admin fora da faixa
```

Não exibir na localização frases como `Operação confirmada há X min`, pois o tempo desde a ativação não define posição nem volta.

---

# 14. Exibição do Micro

`entry_consistencia.py` corrige duas inconsistências visuais antigas:

- `Onde está?` não substitui o estado real do Micro por uma referência escolhida apenas pelo relógio quando não há ponto;
- `Próximos horários` usa a referência armazenada da sessão do Micro, em vez de declarar uma `volta atual` apenas pela hora corrente.

Se o Micro estiver esporádico, mostrar isso claramente.

---

# 15. Fim de bloco e última volta

O relógio não troca voltas intermediárias, mas continua fechando o contexto operacional quando o bloco realmente termina.

Na última volta:

- informar que é a última do bloco;
- indicar retorno/Garagem quando aplicável;
- lembrar que ainda pode passar em pontos do retorno;
- informar a próxima saída do bloco seguinte.

Chegada ao RU na última volta não significa necessariamente Garagem imediata; Fitotecnia/Solos ainda podem ser atendidos no percurso de retorno à Garagem.

Essa regra também deve ser respeitada ao interpretar o Micro quando ele estiver numa última referência oficial de bloco.

---

# 16. Referência especial 20:00

Existe volta de 20:00 baseada na rotina do ano anterior:

```text
20:00 -> previsão, pode não ocorrer
P1 ~20:10–20:15
fim ~20:25
pode passar antes
```

Manter o aviso de que é previsão.

---

# 17. Pedidos colaborativos de confirmação

Quando há silêncio após consultas:

- pelo menos 10 candidatos por disparo;
- normal: primeiro pedido após ~5 min;
- pico: ~10 min;
- segundo disparo aproximadamente 15/20 min;
- máximo 2 avisos por volta;
- nova confirmação cancela/zera o fluxo;
- candidatos podem entrar até ~1 min antes do envio;
- autor da última confirmação pode receber pergunta intermediária ~7/8 min quando aplicável;
- fluxos não se sobrepõem;
- resposta direta ao aviso disponível por 3 min.

Objetivo: buscar evidência quando falta informação, não exigir confirmação a cada ponto.

---

# 18. Administração

`🛠️ Ajuste manual` concentra controles administrativos:

- escolher volta de referência;
- corrigir ponto/sentido;
- corrigir Micro;
- Garagem/encerrar bloco.

Esses controles não devem poluir o menu comum.

---

# 19. Arquivos sensíveis agora

```text
cloudflare/src/entry_consistencia.py
-> exibição final coerente de Principal/Micro

cloudflare/src/entry_antiteleporte.py
-> indicação suspeita, resolução por nova evidência,
   reinício de volta e regras equivalentes para Micro

cloudflare/src/registro_colaborativo.py
-> inferência de rota sem depender do relógio/grade do Principal

cloudflare/src/volta_referencia.py
-> referência persistente; não troca por relógio

cloudflare/src/expiracao_volta.py
-> fechamento real do bloco

cloudflare/src/estado_bus.py
-> camada antiga ainda possui alguns helpers históricos;
   conferir se estão no caminho efetivo antes de reaproveitar

cloudflare/src/micro.py
-> faixa funcional, referências oficiais e ativação

cloudflare/src/dados.py
-> horários e rota
```

---

# 20. Código legado que pode confundir

Durante o pente-fino foram encontrados comportamentos antigos ainda existentes em camadas inferiores, mas substituídos pela camada final:

- heurística temporal de Biblioteca do Micro após 15 min em `estado_bus.py`;
- textos/funções que escolhiam `volta atual do Micro` somente pela hora;
- inferência de próxima volta do Principal por limite temporal em `volta_referencia.py`.

A inferência temporal de próxima volta foi removida diretamente de `volta_referencia.py`.

A lógica do Micro foi sobrescrita no caminho efetivo por `entry_antiteleporte.py` + `registro_colaborativo.py` + `entry_consistencia.py`.

Não copiar o comportamento legado de volta para camadas novas sem revisar estas decisões.

---

# 21. Testes prioritários

```text
PRINCIPAL
1. P1 confiável -> RU rápido -> confirmar
   P1 continua confiável; RU só incerto.

2. P1 -> RU suspeito -> Biblioteca
   RU descartado; Biblioteca assume; volta ainda não acabou.

3. P1 -> RU suspeito -> Fitotecnia/Solos/Pav I
   reconhecer nova volta quando houver próxima referência no mesmo bloco.

4. Biblioteca -> P1 <2 min
   perguntar certeza; nunca bloquear definitivamente.

5. Biblioteca -> P1 suspeito -> Canaã plausível
   Canaã prevalece.

6. volta 11:30 atravessa 11:55/12:00 sem nova evidência
   continua referência 11:30.

7. RU confiável com outra volta no bloco
   fim da volta; Fitotecnia só primeiro esperado.

8. RU -> primeira evidência nova em Solos/Pav I/P2
   aceitar nova volta sem exigir Fitotecnia.

9. última volta do bloco -> RU -> Fitotecnia/Solos
   não inventar nova volta; preservar retorno/Garagem.

MICRO
10. repetir os casos de suspeita acima no Micro.

11. primeira confirmação do Micro = Biblioteca
    sentido deve ficar ambíguo; horário não decide.

12. Micro RU confiável -> nova evidência
    nova volta só quando a rota comprovar.

13. Micro 07:55 -> fim da volta
    não saltar automaticamente para 11:20.

14. Micro ativo sem ponto
    Onde está? deve informar ausência de confirmação e referência da sessão,
    sem inventar posição pelo relógio.

15. Micro esporádico
    pontos continuam aceitos sem usar janelas do Principal.
```

Existe também:

```text
cloudflare/tests/test_registro_colaborativo.py
```

com cobertura básica das novas regras puras de rota.

---

# 22. Commits recentes importantes

```text
511e6aa -> início da reformulação
3090718 -> confirmação suspeita sem bloqueio
2618931 -> horários intermediários deixam de expirar a volta
0f9bedd -> indicação suspeita separada do estado confiável
5623381 -> Micro almoço começa 11:20
8ec434c -> registro colaborativo sem depender do relógio
c7031bb -> novas regras aplicadas também ao Micro
a5406ef -> remove troca de volta apenas pelo relógio
e7d1964 -> exibição do Micro alinhada ao estado colaborativo
12c73f2 -> entry_consistencia passa a ser entrypoint
c389efe -> testes do registro colaborativo
```

---

# 23. Regras que não devem ser quebradas

1. Confirmação confiável > inferência > horário.
2. Horário identifica a volta, mas não troca a volta sozinho.
3. RU confiável encerra volta; não inicia automaticamente outra.
4. Fitotecnia é esperado, não obrigatório.
5. Outro ponto plausível pode provar nova volta.
6. Biblioteca sempre exige contexto.
7. Suspeita nunca bloqueia confirmação correta posterior.
8. Suspeita nunca encerra/inicia volta sozinha.
9. Estado confiável e suspeita ficam separados.
10. Não reintroduzir trava geral de tempo.
11. Principal e Micro seguem a mesma filosofia de evidência.
12. Micro não pode usar a grade do Principal para validar seus pontos.
13. Micro não troca referência só porque o relógio avançou.
14. Não saltar automaticamente entre blocos distantes do Micro.
15. Horário continua forte na abertura/fim operacional.
16. Última volta precisa preservar retorno/Garagem.
17. Usuário não precisa conhecer detalhes internos do algoritmo.
18. Não versionar secrets/IDs administrativos.

---

# 24. Próximo foco

Observar a lógica nova em voltas reais, principalmente:

- retorno x nova volta quando faltam confirmações;
- última volta do bloco x retorno à Garagem;
- Micro esporádico;
- Biblioteca como primeira confirmação;
- resolução de indicações suspeitas por evidência posterior.

Ao surgir caso inesperado, registrar a sequência real de **horários + pontos + veículo** e ajustar a inferência sem transformar horário em GPS nem recriar bloqueios gerais.
