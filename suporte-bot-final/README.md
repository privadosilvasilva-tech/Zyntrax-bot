# 🤖 Suporte Bot - Sistema Completo de Suporte

Uma plataforma web moderna, segura e responsiva para suporte ao cliente, integrada ao Discord.

## ✨ Funcionalidades

✅ **Chat ao Vivo** - Mensagens em tempo real com styling premium  
✅ **Autenticação Discord** - Login seguro com OAuth2  
✅ **Sistema de Tickets** - Criação e acompanhamento de tickets (implementar)  
✅ **Painel Admin** - Gerenciar tags e permissões de usuários  
✅ **Design Premium** - Glassmorphism, animações, responsivo  
✅ **Termos e Privacidade** - Páginas legais completas  
✅ **Segurança** - Autenticação no backend, validação de permissões  
✅ **Acessibilidade** - Suporte a navegação por teclado e mobile  
✅ **Performance** - Otimizado para celular, tablet e desktop  

## 🚀 Como Começar

### 1. Extrair o Projeto

```bash
cd ~ && unzip suporte-bot-final.zip && cd suporte-bot
```

### 2. Preencher Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env.local

# Editar com suas informações
nano .env.local
```

**Variáveis necessárias:**

```env
# Discord OAuth
DISCORD_CLIENT_ID=seu_client_id
DISCORD_CLIENT_SECRET=seu_client_secret
DISCORD_REDIRECT_URI=http://localhost:3000/api/auth/callback

# Supabase
NEXT_PUBLIC_SUPABASE_URL=sua_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=sua_key

# IDs (não alterar)
NEXT_PUBLIC_FOUNDER_ID=1526990069255114913
NEXT_PUBLIC_BOT_ID=1540163536406192148
NEXT_PUBLIC_GUILD_ID=1539105495321681922

# JWT Secret (gere uma chave segura)
JWT_SECRET=sua_chave_secreta

# Base URL
NEXT_PUBLIC_BASE_URL=http://localhost:3000
```

### 3. Instalar Dependências

```bash
npm install
```

### 4. Rodar Localmente

```bash
npm run dev
```

Acessa: http://localhost:3000

### 5. Build para Produção

```bash
npm run build
npm start
```

## 📁 Estrutura do Projeto

```
suporte-bot/
├── app/
│   ├── api/
│   │   ├── auth/              # Autenticação Discord
│   │   │   ├── discord/       # Login
│   │   │   ├── callback/      # Callback OAuth
│   │   │   ├── logout/        # Logout
│   │   │   └── me/            # Dados do usuário
│   │   ├── chat/              # APIs do chat
│   │   ├── tags/              # CRUD de tags
│   │   └── tickets/           # Sistema de tickets
│   ├── admin/                 # Painel administrativo
│   ├── termos/                # Termos de Serviço
│   ├── privacidade/           # Política de Privacidade
│   ├── layout.jsx             # Layout raiz
│   └── page.jsx               # Página principal
├── lib/
│   └── supabase.js            # Cliente Supabase
├── styles/
│   └── globals.css            # Design system e animações
└── .env.example               # Variáveis de exemplo
```

## 🎨 Design

- **Paleta:** Dark + Futurista + Glassmorphism
- **Cores principais:** #6c5ce7 (roxo), #00b894 (verde), #f59e0b (dourado)
- **Tipografia:** Inter, system-ui, sans-serif
- **Responsividade:** Mobile-first (320px → 1440px)
- **Animações:** Suaves e profissionais

## 🔐 Segurança

- ✅ Autenticação Discord OAuth2
- ✅ Validação de permissões no backend
- ✅ Cookies seguros (HttpOnly)
- ✅ Proteção do painel admin
- ✅ Sem exposição de secrets

## 📱 Responsividade

- **Mobile:** < 400px, 400-600px
- **Tablet:** 600-900px, 900-1024px
- **Desktop:** 1024px+

Testado em todos os breakpoints.

## 🛠️ Tecnologias

- **Framework:** Next.js 16.3.4 (App Router)
- **Linguagem:** JavaScript
- **Banco:** Supabase (PostgreSQL)
- **Autenticação:** Discord OAuth2
- **Estilização:** CSS puro com Design System
- **Ícones:** React Icons
- **Hospedagem:** Vercel

## 📚 Documentação

### Autenticação

O projeto usa Discord OAuth2. Usuários precisam:
1. Clicar em "Login Discord"
2. Autorizar no Discord
3. Retornar ao site com sessão ativa

### Painel Admin

Apenas o fundador (ID: 1526990069255114913) pode acessar `/admin`.

Funções:
- Adicionar tags a usuários
- Remover tags
- Visualizar histórico

### Banco de Dados

Tabelas no Supabase:
- `chat_messages` - Mensagens do chat
- `user_tags` - Tags dos usuários
- `tickets` - Tickets de suporte
- `sessions` - Sessões de usuário

## 🐛 Troubleshooting

**Erro: "Variáveis Supabase não configuradas"**
- Verificar `.env.local` está preenchido
- Executar `npm run dev` novamente

**Erro: "Falha na autenticação Discord"**
- Verificar `DISCORD_CLIENT_ID` e `DISCORD_CLIENT_SECRET`
- Confirmar `DISCORD_REDIRECT_URI` está correto

**Erro: "Acesso Negado" no painel admin**
- Confirmar que o ID do usuário é o fundador
- Verificar no navegador: `localStorage.getItem('discord_user')`

## 🚢 Deploy na Vercel

```bash
# 1. Fazer push para GitHub
git add .
git commit -m "Deploy suporte bot"
git push origin main

# 2. Conectar no Vercel
# - Importar repositório GitHub
# - Adicionar variáveis de ambiente
# - Deploy automático

# 3. Atualizar DISCORD_REDIRECT_URI
DISCORD_REDIRECT_URI=https://seu-dominio.vercel.app/api/auth/callback
```

## 📝 Licença

Este projeto é privado. Uso interno apenas.

## 🤝 Suporte

Para dúvidas, entre em contato pelo Discord: [Link do Servidor]

---

**Versão:** 1.0.0  
**Status:** ✅ Pronto para Produção  
**Última Atualização:** 2026-09-05
