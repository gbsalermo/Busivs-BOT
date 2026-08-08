# Setup local

## 1. Clonar e entrar na branch da base Python

```bash
git clone https://github.com/gbsalermo/Busivs-BOT.git
cd Busivs-BOT
git checkout feat/python-base
```

## 2. Criar ambiente virtual

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Instalar dependências

```bash
pip install -r requirements.txt
```

## 4. Configurar token do Telegram

Copie `.env.example` para `.env` e substitua o valor de `TELEGRAM_BOT_TOKEN` pelo token fornecido pelo BotFather.

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### Linux/macOS

```bash
cp .env.example .env
```

Exemplo:

```env
TELEGRAM_BOT_TOKEN=123456:ABCDEF
```

Nunca faça commit do arquivo `.env`.

## 5. Executar

```bash
python src/bot.py
```

Se estiver tudo correto, o terminal mostrará `BUSIVS BOT iniciado.` e o comando `/start` no Telegram exibirá o menu inicial.

## Escopo desta etapa

Esta base implementa somente:

- carregamento de configuração;
- token via `.env`;
- logging;
- inicialização do bot via polling;
- comando `/start`;
- menu inicial;
- arquivos estáticos preparados para pontos, horários e rotas.

Os botões ainda não executam ações. Isso entra nas próximas etapas.
