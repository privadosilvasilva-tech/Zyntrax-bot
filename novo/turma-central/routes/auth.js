const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const rateLimit = require('express-rate-limit');
const { get, run } = require('../db');
const { requireAuth, asyncRoute } = require('../middleware/auth');
const { JWT_SECRET } = require('../db/secret');

const router = express.Router();

// No máximo 8 tentativas de login por IP a cada 10 minutos.
const loginLimiter = rateLimit({
  windowMs: 10 * 60 * 1000,
  max: 8,
  message: { error: 'Muitas tentativas de login. Tente novamente em alguns minutos.' },
  standardHeaders: true,
  legacyHeaders: false,
});

async function logAction(userId, action, targetId) {
  await run('INSERT INTO logs (user_id, action, target_id) VALUES (?, ?, ?)', userId, action, targetId || null);
}

function setSessionCookie(res, token) {
  res.cookie('token', token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    maxAge: 7 * 24 * 60 * 60 * 1000,
  });
}

// Primeira vez usando o site: se ainda não existe NENHUM usuário, libera a
// criação da conta do proprietário direto pela tela (sem precisar editar
// arquivos nem rodar comandos). Depois que o primeiro usuário existe, essa
// rota nunca mais aceita criar outro por aqui.
router.get('/setup-status', asyncRoute(async (req, res) => {
  const row = await get('SELECT COUNT(*) as count FROM users');
  res.json({ needsSetup: row.count === 0 });
}));

router.post('/setup', asyncRoute(async (req, res) => {
  const row = await get('SELECT COUNT(*) as count FROM users');
  if (row.count > 0) {
    return res.status(403).json({ error: 'A configuração inicial já foi concluída.' });
  }
  const { username, password, display_name } = req.body || {};
  if (!username || !password || !display_name) {
    return res.status(400).json({ error: 'Preencha todos os campos.' });
  }
  if (password.length < 6) {
    return res.status(400).json({ error: 'A senha precisa ter pelo menos 6 caracteres.' });
  }
  const hash = bcrypt.hashSync(password, 12);
  const cleanUsername = username.trim().toLowerCase();
  const info = await run(
    `INSERT INTO users (username, password_hash, display_name, role) VALUES (?, ?, ?, 'owner')`,
    cleanUsername, hash, display_name
  );

  await logAction(info.lastInsertRowid, 'CRIOU_CONTA_PROPRIETARIO_SETUP');

  const token = jwt.sign({ id: info.lastInsertRowid, role: 'owner' }, JWT_SECRET, { expiresIn: '7d' });
  setSessionCookie(res, token);
  res.status(201).json({
    user: { id: info.lastInsertRowid, username: cleanUsername, display_name, role: 'owner' },
  });
}));

router.post('/login', loginLimiter, asyncRoute(async (req, res) => {
  const { username, password } = req.body || {};
  if (!username || !password) {
    return res.status(400).json({ error: 'Informe usuário e senha.' });
  }

  const user = await get('SELECT * FROM users WHERE username = ?', username.trim().toLowerCase());
  if (!user) {
    return res.status(401).json({ error: 'Usuário ou senha incorretos.' });
  }

  if (user.locked_until && new Date(user.locked_until) > new Date()) {
    return res.status(423).json({ error: 'Conta temporariamente bloqueada por muitas tentativas erradas. Tente mais tarde.' });
  }

  const ok = bcrypt.compareSync(password, user.password_hash);
  if (!ok) {
    const attempts = user.failed_attempts + 1;
    let lockedUntil = null;
    if (attempts >= 5) {
      lockedUntil = new Date(Date.now() + 15 * 60 * 1000).toISOString();
    }
    await run('UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?', attempts, lockedUntil, user.id);
    return res.status(401).json({ error: 'Usuário ou senha incorretos.' });
  }

  await run('UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?', user.id);

  const token = jwt.sign({ id: user.id, role: user.role }, JWT_SECRET, { expiresIn: '7d' });
  setSessionCookie(res, token);

  await logAction(user.id, 'LOGIN');

  res.json({
    user: { id: user.id, username: user.username, display_name: user.display_name, role: user.role },
  });
}));

router.post('/logout', requireAuth, asyncRoute(async (req, res) => {
  await logAction(req.user.id, 'LOGOUT');
  res.clearCookie('token');
  res.json({ ok: true });
}));

router.get('/me', requireAuth, (req, res) => {
  res.json({ user: req.user });
});

module.exports = router;
