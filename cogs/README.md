# 🛡️ SISTEMA DE MODERAÇÃO ZYNTRAX

Pacote completo com 6 painéis de configuração de moderação para o bot Zyntrax.

## 📦 Conteúdo do Pacote

```
cogs/
├── configuracoes.py      ✨ Painel principal atualizado
├── moderacao.py          🛡️  Sub-painel de moderação
├── filtro_palavras.py    🚫 Bloqueio de palavras personalizadas
├── antilink.py           🔗 Bloqueio de convites de servidores
├── antispam.py           ⚠️  Proteção contra spam
├── antiraid.py           🚨 Proteção contra ataques em massa
├── infracoes.py          📋 Sistema de infrações
└── logs_moderacao.py     📊 Logs de moderação
```

## 🚀 INSTALAÇÃO RÁPIDA

### Passo 1: Copiar os arquivos

No Termux, execute:

```bash
cd ~/zyntrax-bot

# Copiar todos os arquivos da pasta cogs
cp cogs/configuracoes.py cogs/configuracoes.py.bak  # Fazer backup do antigo
cp /caminho/do/zip/extraido/cogs/* cogs/
```

Ou simplesmente extraia o ZIP diretamente na pasta `cogs/`:

```bash
cd ~/zyntrax-bot/cogs
unzip ~/storage/downloads/zyntrax-moderacao.zip
```

### Passo 2: Verificar sintaxe

```bash
cd ~/zyntrax-bot
python3 -m py_compile cogs/*.py && echo "✅ OK, sem erro de sintaxe"
```

### Passo 3: Reiniciar o bot

```bash
pkill -f bot.py
python3 bot.py
```

## 📋 COMO USAR

### 1️⃣ Acessar o painel de configurações

No Discord, execute:

```
/configuracoes
```

### 2️⃣ Clicar em "🛡️ Moderação"

Abre o sub-painel com 6 opções:

- **🚫 Filtro de Palavras** - Bloqueie palavras personalizadas
- **🔗 Anti-Link** - Bloqueie convites de outros Discord
- **⚠️ Anti-Spam** - Proteção contra mensagens repetidas
- **🚨 Anti-Raid** - Bloqueie ataques em massa
- **📋 Infrações** - Configure níveis de punição
- **📊 Logs** - Configure canal de logs

### 3️⃣ Configurar cada painel

Cada painel tem:
- ✅ Status (Ativado/Desativado)
- 🎚️ Botões para ajustar limites
- 👥 Seletores para membros/bots
- 💾 Botão "Salvar"
- ◀️ Botão "Voltar"

## 🎯 DETALHES DE CADA PAINEL

### 🚫 Filtro de Palavras
- Adicione **unlimited** palavras para bloquear
- Configure mensagem de aviso personalizada
- Ativa/desativa automaticamente
- Deleta mensagens e avisa o usuário

### 🔗 Anti-Link de Servidores
- Bloqueie convites de outros Discord
- Configure membros com permissão
- Configure bots com permissão
- **Bot Zyntrax sempre permitido** (automático)
- Detecta: `discord.gg/...` e `discord.com/invite/...`

### ⚠️ Anti-Spam
- Detecta mensagens repetidas (configurável 1-10x)
- Detecta CAPS LOCK excessivo (configurável 50-100%)
- Ajusta limites com botões ➕ e ➖
- Deleta automaticamente

### 🚨 Anti-Raid
- Detecta múltiplas entradas em pouco tempo
- Configure limite de joins (1-50)
- Configure janela de tempo (1-60 segundos)
- Ativa slowmode automaticamente

### 📋 Sistema de Infrações
- Escalonamento de punições automático
- Warn → Timeout → Kick → Ban

### 📊 Logs de Moderação
- Selecione canal para registros
- Registra: warns, timeouts, kicks, bans
- Também registra spam bloqueado e links deletados

## ⚙️ CONFIGURAÇÃO SALVA

Todos os dados são salvos em:

```
~/zyntrax-bot/config/moderacao_config.json
```

Backup automático recomendado!

## 🔑 PERMISSÕES NECESSÁRIAS

O bot precisa dessas permissões:

- `Gerenciar Mensagens` - Deletar mensagens
- `Moderação` - Timeout, kick, ban
- `Gerenciar Canais` - Ativar slowmode
- `Enviar Mensagens` - Para avisos

## ❓ DÚVIDAS COMUNS

**P: O bot consegue dar timeout automaticamente?**
R: Sim! Anti-Spam e Anti-Raid ativam timeout automático quando detectam infração.

**P: Posso whitelist membros para enviar convites?**
R: Sim! No painel de Anti-Link, selecione membros e bots com permissão.

**P: O bot Zyntrax pode ser bloqueado?**
R: Não, ele sempre tem permissão (automático).

**P: Como reseto as configurações?**
R: Delete o arquivo `config/moderacao_config.json` e reinicie o bot.

## 📞 SUPORTE

Se tiver problemas:

1. Verifique se todos os arquivos foram copiados
2. Rode `python3 -m py_compile cogs/*.py`
3. Confira os logs do bot no terminal
4. Verifique permissões do bot no Discord

## 🎉 Pronto!

Seu sistema de moderação está ativo e funcionando! Aproveite!

---

**Versão:** 1.0  
**Data:** 2026  
**Bot:** Zyntrax
