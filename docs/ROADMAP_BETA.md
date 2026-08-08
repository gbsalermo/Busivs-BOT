# Roadmap até a versão Beta

## Etapa 0 - Especificação ✅

- [x] Telegram como interface
- [x] Python como linguagem
- [x] SQLite para estado persistente
- [x] JSON para dados fixos
- [x] localização manual + NFC
- [x] Principal + Micro
- [x] previsão baseada na última passagem
- [x] suporte futuro a portões, férias e avisos
- [ ] validar nomes e ordem dos pontos
- [ ] transcrever horários oficiais
- [ ] validar quais horários são volta completa e volta curta

## Etapa 1 - Base do bot

- [ ] criar ambiente Python
- [ ] configurar `.env`
- [ ] registrar token do bot
- [ ] implementar `/start`
- [ ] criar menu inline
- [ ] carregar JSON de configuração
- [ ] logging básico

## Etapa 2 - Horários fixos

- [ ] cadastrar horários do Principal
- [ ] cadastrar horários previstos do Micro
- [ ] identificar próximo horário
- [ ] primeira e última saída
- [ ] diferenciar dia útil
- [ ] preparar `LETIVO` e `FERIAS`

## Etapa 3 - Pontos e rota

- [ ] cadastrar pontos
- [ ] ordem
- [ ] tempos estimados entre pontos
- [ ] volta completa
- [ ] volta curta
- [ ] pontos opcionais
- [ ] identificar próxima parada

## Etapa 4 - Autenticação institucional

- [ ] receber e-mail
- [ ] validar domínio institucional
- [ ] gerar código temporário
- [ ] enviar código
- [ ] validar código
- [ ] persistir `telegram_id`
- [ ] limitar tentativas
- [ ] expirar código

## Etapa 5 - `/local`

- [ ] selecionar Principal/Micro
- [ ] selecionar ponto
- [ ] confirmar
- [ ] salvar registro
- [ ] impedir spam imediato
- [ ] validar coerência mínima da sequência
- [ ] atualizar estado do veículo

### Primeiro protótipo utilizável

Ao final desta etapa já é possível testar com alunos.

## Etapa 6 - ETA / previsão

- [ ] tempo base entre pontos
- [ ] calcular ETA cumulativo
- [ ] recalcular após nova confirmação
- [ ] indicar idade da informação
- [ ] classificar confiabilidade
- [ ] zerar estado ao encerrar operação diária

## Etapa 7 - NFC

- [ ] definir formato dos deep links
- [ ] gerar identificadores das tags
- [ ] testar leitura Android
- [ ] confirmar ponto vindo do `/start`
- [ ] impedir alteração do ponto recebido
- [ ] marcar origem `NFC`

## Etapa 8 - Principal + Micro

- [ ] estado independente por veículo
- [ ] Principal sempre esperado
- [ ] Micro começa `NAO_CONFIRMADO`
- [ ] primeira confirmação ativa Micro
- [ ] ausência vira `PROVAVELMENTE_INATIVO`
- [ ] confirmação tardia reativa
- [ ] mensagens deixam clara a incerteza

## Etapa 9 - Desvios de portões

- [ ] `NORMAL`
- [ ] `PORTAO_1_FECHADO`
- [ ] `PORTAO_2_FECHADO`
- [ ] arquivos de rotas alternativas
- [ ] comando administrativo para alterar modo
- [ ] ETA usa rota ativa
- [ ] aviso automático de alteração

## Etapa 10 - Férias

- [ ] calendário `LETIVO/FERIAS`
- [ ] horários de férias
- [ ] comando administrativo
- [ ] mensagem visível ao usuário

## Etapa 11 - Avisos

- [ ] avisos manuais
- [ ] mensagem de bom dia
- [ ] alertas de rota
- [ ] chuva/calor manual no primeiro momento
- [ ] opcional: API meteorológica

# Beta

A versão Beta deve ter horários oficiais validados, Principal, Micro com regra de incerteza, autenticação institucional, `/local`, NFC, ETA, indicador de atualização/confiança, rotas de desvio, modo férias, avisos, logs, tratamento de erros, política básica de privacidade e teste piloto com estudantes.

## Fora do Beta

Não desenvolver antes de haver necessidade real:

- aplicativo mobile próprio
- frontend web
- PostgreSQL
- microserviços
- GPS embarcado
- machine learning
- mapa em tempo real
