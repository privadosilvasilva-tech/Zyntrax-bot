# 🎫 Zyntrax Tickets — Atualização: Canal do Painel + Canal de Logs

## Instalar (Termux)

```bash
cd ~/zyntrax-bot
mkdir -p ~/tickets-pkg
unzip ~/storage/downloads/zyntrax-tickets-ajuste.zip -d ~/tickets-pkg
bash ~/tickets-pkg/atualizar_tickets.sh
pkill -f bot.py
python3 bot.py
```

## O que mudou

No `/configuracoes` -> **🎫 Tickets**, agora existem dois seletores de canal
separados (antes só existia "publicar aqui"):

- **📍 Canal do Painel** — onde o menu público de abertura de atendimento
  vai ficar. Escolha o canal e só depois clique em **🚀 Publicar Painel no
  Canal Selecionado**.
- **🗂️ Canal de Logs** — um único canal que recebe:
  - 🟢 aviso quando um ticket é **aberto** (autor, categoria, prioridade)
  - 🔒 aviso quando um ticket é **encerrado** (resultado, duração)
  - 📄 o **transcript** completo (.txt) daquele atendimento

Se você já tinha configurado um "canal de transcripts" antes, ele é migrado
automaticamente para o novo "canal de logs" — não precisa reconfigurar.

Os **cargos marcados em cada categoria** (quem é notificado quando um ticket
daquele tipo é aberto) já existiam e continuam do mesmo jeito: em
`/configuracoes -> 🎫 Tickets -> ✏️ Gerenciar Categorias -> escolha a
categoria -> 👥 Equipe responsável (seletor de cargos)`. Me manda os
detalhes que faltaram (a mensagem cortou) que eu ajusto certinho.
