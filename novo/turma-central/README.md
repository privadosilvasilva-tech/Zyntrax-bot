# Central da Turma

Site para gerenciar atividades, prazos, avisos e chat em tempo real de uma turma.

## O que já funciona de verdade

- Login com usuário/senha (bcrypt, cookie de sessão assinado com JWT, bloqueio após 5 tentativas erradas, limite de tentativas por IP).
- 4 papéis: proprietário (👑), administrador (🛠️), suporte (🆘) e aluno (👤), cada um com permissões diferentes checadas **no servidor** (nunca só no navegador).
- Atividades/trabalhos/avisos com ID automático (ATV-001, TRB-002...), anexos, status calculado automaticamente pela data de entrega.
- Calendário mensal com os prazos.
- Chat em tempo real (Socket.io) com histórico salvo no banco e carregamento progressivo.
- Painel administrativo, painel exclusivo do proprietário e logs de ações importantes.
- Modo claro/escuro e layout responsivo (celular, tablet, computador).
- Música de fundo tocando direto do YouTube em loop, com botão de som (veja a seção "Música" abaixo — navegadores bloqueiam áudio com som sem interação do usuário, isso não é uma limitação deste projeto específico, é regra de todo navegador).
- **Quase não precisa configurar nada manualmente**: a chave de segurança das sessões é gerada sozinha na primeira vez que o servidor liga, e a conta do proprietário é criada direto pela tela do site. O único passo manual que sobrou é criar um banco de dados gratuito (leva 2 minutos, veja abaixo) — assim os dados nunca somem, nem quando você atualizar o site.

## 0. Banco de dados (Neon — gratuito, guarda os dados pra sempre)

Esse site guarda usuários, atividades e o chat num banco de dados. Escolhi o **Neon**: é Postgres na nuvem, gratuito pra sempre (sem cartão), e é o que garante que nada se perde quando você atualizar o código ou reiniciar o servidor — diferente de guardar o banco só no disco do servidor.

1. Crie uma conta grátis em **https://neon.tech** (dá pra entrar com GitHub).
2. Clique em **Create a project**, dê um nome (ex: `turma-central`) e confirme.
3. Assim que o projeto for criado, o painel já mostra a **connection string** completa (algo como `postgresql://usuario:senha@ep-xxxx.neon.tech/neondb?sslmode=require`) — copie ela inteira.
4. Cole no arquivo `.env` do projeto (copie `.env.example` para `.env` primeiro), na variável `DATABASE_URL`.

Pronto — o site cria as tabelas sozinho na primeira vez que liga.

## 1. Instalar e rodar localmente

Pré-requisito: [Node.js](https://nodejs.org) versão 18 ou mais recente, e o banco Neon já criado (passo 0 acima).

```bash
cd turma-central
cp .env.example .env
# edite o .env e cole a DATABASE_URL do Neon
npm install
npm start
```

Não precisa gerar chave nenhuma nem rodar `npm run seed` — a chave de sessão e a conta do proprietário o site cuida sozinho. Acesse **http://localhost:3000**: como é a primeira vez, vai aparecer uma tela pedindo para criar a conta do **proprietário** (nome, usuário e senha). Depois de criada, você já entra automaticamente logado como proprietário e essa tela nunca mais aparece.

A partir daí, crie as contas de administradores, suporte e alunos direto pelo Painel administrativo (👥 Usuários → Criar usuário).

## 2. Música de fundo

A música toca direto do vídeo do YouTube que você escolheu, sem precisar baixar nem hospedar nenhum arquivo de áudio (o player fica escondido na página, só o som é usado).

Como todo navegador bloqueia som automático sem interação do usuário, a música entra tocando **mutada** assim que a página abre, e existe um botão flutuante (🔈/🔊) no canto superior direito: no primeiro clique o som é liberado, e a partir daí ela toca em loop, reiniciando sozinha sempre que a faixa terminar. Ela continua tocando enquanto a pessoa navega pelas páginas do site dentro da mesma aba — nenhum site, porém, consegue continuar tocando som com a aba ou o navegador fechados, isso não é algo que dê pra contornar.

Para trocar a música depois, basta editar a constante `BGM_VIDEO_ID` no topo de `public/js/app.js` com o ID de outro vídeo do YouTube.

## 3. Enviar para o GitHub

O projeto já vem com um repositório git iniciado e o primeiro commit feito (o `.gitignore` garante que `.env`, o banco de dados e os arquivos de upload nunca vão parar no GitHub). Para enviar:

1. Crie um repositório novo e **vazio** no GitHub (sem README, sem .gitignore — já tem esses arquivos aqui). Nome sugerido: `Turma7-b` (o GitHub não aceita o símbolo `°` em nomes de repositório, só letras, números, hífen, underscore e ponto). Copie a URL do repositório depois de criado.
2. No terminal, dentro da pasta do projeto:

```bash
git remote add origin https://github.com/seu-usuario/Turma7-b.git
git branch -M main
git push -u origin main
```

3. Pronto — o código está no GitHub. **Confira lá que o arquivo `.env` não aparece na lista** (ele nunca deve aparecer; só o `.env.example` deve estar visível).

Depois disso, na hospedagem escolhida você conecta esse mesmo repositório do GitHub (ou envia o ZIP) e cadastra `DATABASE_URL` e `NOME_DA_TURMA` direto no painel da plataforma — nunca dentro do código. Não precisa mais de `JWT_SECRET`, `OWNER_USERNAME` nem `OWNER_PASSWORD`.

## 4. Colocar o site no ar (hospedagem)

Este projeto precisa rodar num servidor Node.js com processo contínuo (não é um site estático, e o chat em tempo real via Socket.io precisa de uma conexão que fique aberta — por isso não funciona em hospedagens 100% serverless como a Vercel). Funciona bem em qualquer host que rode Node.js sem parar, como **Render.com** ou **Inject Cloud**, ambos com plano gratuito.

1. Crie uma conta na hospedagem escolhida e conecte o repositório do GitHub, ou envie o `.zip` do projeto direto (algumas hospedagens aceitam as duas formas).
2. Comando de build: `npm install`. Comando de start: `npm start`.
3. Nas variáveis de ambiente do painel, adicione `DATABASE_URL` (a connection string do Neon), `NOME_DA_TURMA` e `NODE_ENV=production`.
4. Deploy. Pronto — como os dados ficam no Neon (fora do servidor), eles **não se perdem** mesmo quando você atualizar o código e a hospedagem fizer um novo deploy.

**Atenção com os anexos de atividades**: os arquivos enviados nas publicações (`public/uploads`) ainda ficam salvos no disco do próprio servidor, não no Neon. Em planos gratuitos, esse disco costuma ser apagado a cada novo deploy — ou seja, os *registros* das atividades permanecem, mas um anexo enviado antes de um deploy pode deixar de existir depois. Se isso for importante pra vocês, me avise depois que eu adapto os uploads para um serviço de armazenamento gratuito também (ex: Cloudflare R2).

## 5. Estrutura do projeto

```
server.js              → servidor Express + Socket.io
db/schema.sql           → estrutura das tabelas
db/index.js              → conexão com o banco Neon (Postgres)
db/secret.js             → gera e guarda a chave de sessão automaticamente
middleware/auth.js       → autenticação e checagem de permissões
routes/auth.js           → login/logout/configuração inicial
routes/users.js          → gerenciar usuários (criar/editar/excluir/papéis)
routes/activities.js     → atividades/trabalhos/avisos + upload de anexos
routes/chat.js            → histórico de mensagens
routes/logs.js            → registros administrativos (painel do proprietário)
public/                   → frontend (HTML, CSS, JS puro, sem build)
```

## 6. Segurança — o que já está implementado

- Senhas: nunca em texto puro, sempre com `bcrypt`.
- Sessão: cookie `httpOnly`, assinado com `JWT_SECRET` (que não fica no código).
- Permissões: checadas em cada rota da API no servidor — o frontend só esconde botões, quem garante mesmo é o backend.
- Rate limiting no login (8 tentativas por IP a cada 10 min) + bloqueio de conta após 5 senhas erradas seguidas.
- Upload de arquivo com limite de tamanho (15 MB) e lista de extensões permitidas.
- Proteção contra SQL Injection: todas as consultas usam parâmetros (prepared statements do driver do Postgres), nunca concatenação de string.

## 7. Próximos passos que você pode pedir para expandir

- Notificações push via PWA (dá pra adicionar depois com um Service Worker).
- Exportar relatórios de atividades.
- Editar/excluir suas próprias mensagens no chat.
