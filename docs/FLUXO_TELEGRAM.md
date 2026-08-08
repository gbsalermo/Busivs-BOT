# Fluxo do Telegram

## 1. Primeiro acesso

```text
/start
  ↓
Olá! Eu sou o BUSIVS 🚌

[ 🚌 Onde está o ônibus? ]
[ 📍 Informar passagem ]
[ ⏰ Próximos horários ]
[ 🗺️ Rota atual ]
[ 📢 Avisos ]
```

A consulta pode funcionar sem cadastro. Ao tentar informar passagem, o bot verifica autenticação.

## 2. Autenticação

```text
📍 Informar passagem
        ↓
Usuário não autenticado
        ↓
"Para confirmar a passagem do ônibus, valide seu e-mail institucional."
        ↓
[ Validar e-mail ]
        ↓
aluno@....ufrb...
        ↓
envio de código
        ↓
123456
        ↓
✅ Conta validada
```

Depois disso o Telegram fica vinculado ao e-mail.

## 3. Informar localização manualmente

Comando `/local` ou botão `📍 Informar passagem`.

```text
Qual ônibus você está vendo?

[ 🚌 Principal ]
[ 🚐 Micro ]
        ↓
Em qual ponto ele acabou de passar?

[ 01 ] [ 02 ] [ 03 ]
[ 04 ] [ 05 ] [ 06 ]
[ 07 ] [ 08 ] [ 09 ]
[ 10 ] [ 11 ] [ 12 ]
        ↓
Ponto 06 - Biblioteca?

[ ✅ Confirmar ]
[ ❌ Cancelar ]
        ↓
✅ Passagem registrada.
```

## 4. Informar via NFC

Tag do ponto contém um deep link:

```text
https://t.me/BUSIVS_BOT?start=local_P06
```

Fluxo:

```text
NFC
 ↓
Telegram abre
 ↓
bot identifica P06
 ↓
usuário autenticado?
 ├─ não -> autenticação
 └─ sim
      ↓
"Confirmar que o ônibus passou no P06?"
      ↓
[ Principal ] [ Micro ]
      ↓
[ ✅ Confirmar ]
```

NFC e `/local` terminam na mesma função de registro.

## 5. Onde está o ônibus?

Botão `🚌 Onde está o ônibus?` ou `/onde`.

```text
Qual veículo?

[ 🚌 Principal ]
[ 🚐 Micro ]
```

Resposta esperada:

```text
🚌 Principal - saída 17:30

📍 Última confirmação:
Biblioteca
17:48 (há 3 min)

➡️ Próximo ponto:
Pavilhão II

⏱️ Previsão:
aprox. 4 min

🟢 Atualização recente
```

## 6. Próximos horários

`/horarios`

```text
⏰ Principal

Próxima saída: 18:10
Depois: 18:50

Primeira do dia: XX:XX
Última do dia: XX:XX

[ 🚐 Ver Micro ]
```

## 7. Regra diária do Micro

Início do dia:

```text
Micro = NAO_CONFIRMADO
```

Primeira passagem válida:

```text
Micro = ATIVO
```

Se a janela configurada da primeira operação passar sem confirmação:

```text
Micro = PROVAVELMENTE_INATIVO
```

Mensagem:

```text
🚐 Micro

Ainda não tivemos nenhuma confirmação hoje.
É provável que o Micro não esteja operando.
```

Uma confirmação posterior muda imediatamente para `ATIVO`.

## 8. Rota atual

`/rota`

Normal:

```text
🗺️ Rota atual: NORMAL

Garagem
→ trecho interno
→ Portão 2
→ trecho externo
→ Portão 1
→ retorno

✅ Sem alteração informada.
```

## 9. Férias

Pós-protótipo.

```text
🏖️ Período de férias

O Circular está operando com horários reduzidos.

[ ⏰ Ver horários ]
```

## 10. Avisos

`/avisos`

```text
🌧️ Bom dia!
Há previsão de chuva hoje.
Leve um guarda-chuva ou capote ☔

🚌 Circular operando normalmente.
```

## Comandos planejados

```text
/start      Menu
/onde       Última posição + ETA
/local      Informar passagem
/horarios   Próximos horários
/rota       Rota ativa
/avisos     Avisos
/ajuda      Explicação do sistema
```

Os botões são a UX principal; comandos funcionam como atalhos.
