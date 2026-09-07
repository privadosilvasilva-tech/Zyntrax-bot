# Zyntrax Bot

## Instalação (Termux)

```bash
pkg update -y
pkg install python git -y
pip install -r requirements.txt
```

## Configuração

```bash
cp .env.example .env
nano .env
```

Cole o token do bot no lugar de `coloque_seu_token_aqui` e salve (`Ctrl+O`, `Enter`, `Ctrl+X`).

## Rodar

```bash
termux-wake-lock
python3 bot.py
```

O `termux-wake-lock` evita que o Android suspenda o processo quando você troca de app (ex: abre o Discord pra testar um botão).

## Rodar em segundo plano com PM2 (recomendado)

```bash
pkg install nodejs -y
npm install -g pm2
pm2 start bot.py --name zyntrax-bot --interpreter python3
pm2 save
```

Comandos úteis:
```bash
pm2 list                        # ver processos
pm2 logs zyntrax-bot            # ver logs em tempo real
pm2 restart zyntrax-bot         # reiniciar
pm2 stop zyntrax-bot            # parar
```

## Estrutura

```
bot.py              -> ponto de entrada, carrega os cogs automaticamente
cogs/test.py         -> /ping
cogs/logs.py          -> /logs (sistema completo de logs do servidor)
config/settings.json -> configurações gerais
config/logs_config.json -> gerado automaticamente pelo /logs (não editar manualmente)
```

## Erros e diagnóstico

Todo erro (comando, botão, select) agora é registrado no console com traceback
completo em vez de falhar silenciosamente. Se algo der "não respondeu a tempo"
no Discord, olha o terminal — o erro real vai aparecer lá.
