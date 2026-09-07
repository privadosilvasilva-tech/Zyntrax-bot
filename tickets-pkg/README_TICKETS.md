# 🎫 Zyntrax SmartDesk — Sistema de Tickets

## 🚀 Instalação (Termux)

```bash
cd ~/zyntrax-bot        # pasta raiz do projeto, onde fica o bot.py
unzip ~/storage/downloads/zyntrax-tickets-smartdesk.zip -d /tmp/tickets-pkg
bash /tmp/tickets-pkg/instalar_tickets.sh
pkill -f bot.py
python3 bot.py
```

O script cria `cogs/tickets.py` e atualiza `cogs/configuracoes.py` (adiciona o botão
"🎫 Tickets" no painel principal). Ele já roda `py_compile` no final para garantir
que não ficou nenhum erro de sintaxe.

## ⚙️ Como configurar

1. Rode `/configuracoes` no servidor.
2. Clique em **🎫 Tickets**.
3. Clique em **➕ Nova Categoria** para cada tipo de atendimento (Suporte, Bug,
   Denúncia, Parceria, Financeiro, etc). Para cada uma dá pra definir:
   - Nome, emoji e descrição
   - Até 5 perguntas do formulário (aparecem antes de o ticket ser criado)
   - Prioridade padrão (baixa/normal/alta/crítico)
   - Categoria do Discord onde o canal do ticket vai nascer
   - Cargos da equipe responsável por aquele tipo de atendimento
4. Defina o **canal de transcripts** (opcional) e a **categoria padrão** do Discord
   (usada quando uma categoria de atendimento não tem categoria própria).
5. Ajuste **Limites e Cooldown** (tickets simultâneos por pessoa, cooldown entre
   aberturas, tempo para avisar que um ticket está sem resposta).
6. Clique em **🚀 Publicar Painel Aqui**, dentro do canal onde os membros vão abrir
   atendimentos. Isso publica o menu de seleção.

## 🧩 O que o sistema faz

- **Abertura inteligente**: menu de seleção por categoria → formulário (modal) →
  canal criado automaticamente com as respostas já organizadas em embed.
- **Prioridade e status reais**: 🟡 Aguardando → 🔵 Em atendimento →
  🟣 Aguardando usuário → 🟠 Em análise → 🟢 Resolvido → ⚫ Encerrado, tudo
  editável por select menu dentro do ticket.
- **Assumir atendimento**: botão 🟢 Assumir vincula o staff ao ticket; a primeira
  mensagem de um staff já marca automaticamente "primeira resposta" pra métricas.
- **Resolver / Encerrar**: abre um modal pedindo o resumo/solução, gera um resumo
  automático no canal, envia o transcript (.txt) pro canal configurado, tranca o
  canal e pede avaliação de 1 a 5 estrelas (+ comentário opcional) pro autor.
- **Aviso de SLA**: se um ticket passar do tempo configurado sem nenhuma resposta
  da equipe, o bot avisa automaticamente marcando a equipe responsável.
- **Anti-abuso**: limite de tickets simultâneos por usuário e cooldown entre
  aberturas.
- **Dashboard**: botão 📊 no painel (ou `/ticket-dashboard`) mostra total de
  tickets, tickets por status, tempo médio de primeira resposta e de resolução,
  nota média de satisfação e um ranking dos atendentes por tickets resolvidos.

## 📁 Onde ficam os dados

- `config/tickets_config.json` — categorias, canais, limites (configuração).
- `config/tickets_data.json` — cada ticket criado, com histórico completo
  (perguntas/respostas, quem assumiu, tempos, avaliação). Isso é o que alimenta
  o dashboard — nunca é apagado ao fechar um ticket.

## 💡 Limitações atuais (pra próxima etapa, se quiser evoluir)

- Cada categoria aceita até 5 perguntas (limite do modal do Discord).
- O "resumo automático" do atendimento é preenchido pelo staff ao fechar
  (sem IA), não é gerado por inteligência artificial.
- O ticket encerrado não é excluído automaticamente — fica trancado no canal
  até um admin apagar manualmente (dá pra evoluir isso depois, se quiser, com
  exclusão automática após X horas).
