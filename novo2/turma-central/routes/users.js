const express = require('express');
const bcrypt = require('bcryptjs');
const { get, all, run } = require('../db');
const { requireAuth, requireRole, asyncRoute } = require('../middleware/auth');

const router = express.Router();
router.use(requireAuth);

async function logAction(userId, action, targetId) {
  await run('INSERT INTO logs (user_id, action, target_id) VALUES (?, ?, ?)', userId, action, targetId || null);
}

// Suporte só pode listar/visualizar; criar e editar contas é para admin+.
router.get('/', requireRole('support'), asyncRoute(async (req, res) => {
  const users = await all('SELECT id, username, display_name, role, created_at FROM users ORDER BY id');
  res.json({ users });
}));

router.post('/', requireRole('admin'), asyncRoute(async (req, res) => {
  const { username, password, display_name, role } = req.body || {};
  if (!username || !password || !display_name || !role) {
    return res.status(400).json({ error: 'Preencha todos os campos.' });
  }
  if (!['owner', 'admin', 'support', 'aluno'].includes(role)) {
    return res.status(400).json({ error: 'Papel inválido.' });
  }
  // Um administrador auxiliar não pode criar outro administrador ou o proprietário.
  if (req.user.role === 'admin' && (role === 'admin' || role === 'owner')) {
    return res.status(403).json({ error: 'Apenas o proprietário pode criar administradores ou outro proprietário.' });
  }
  if (role === 'owner') {
    return res.status(403).json({ error: 'Só pode existir um proprietário. Use a área de configurações para transferir o cargo.' });
  }

  const cleanUsername = username.trim().toLowerCase();
  const exists = await get('SELECT id FROM users WHERE username = ?', cleanUsername);
  if (exists) return res.status(409).json({ error: 'Esse nome de usuário já existe.' });

  const hash = bcrypt.hashSync(password, 12);
  const info = await run(
    'INSERT INTO users (username, password_hash, display_name, role, created_by) VALUES (?, ?, ?, ?, ?)',
    cleanUsername, hash, display_name, role, req.user.id
  );

  await logAction(req.user.id, 'CRIOU_USUARIO', String(info.lastInsertRowid));
  res.status(201).json({ id: info.lastInsertRowid });
}));

router.put('/:id', asyncRoute(async (req, res) => {
  const targetId = Number(req.params.id);
  const target = await get('SELECT * FROM users WHERE id = ?', targetId);
  if (!target) return res.status(404).json({ error: 'Usuário não encontrado.' });

  const isSelf = req.user.id === targetId;
  if (!isSelf && req.user.role !== 'admin' && req.user.role !== 'owner') {
    return res.status(403).json({ error: 'Você não tem permissão para editar outras contas.' });
  }
  if (target.role === 'owner' && req.user.role !== 'owner') {
    return res.status(403).json({ error: 'Só o proprietário pode editar a própria conta.' });
  }
  const { display_name, password, role } = req.body || {};

  if (role && role !== target.role) {
    if (req.user.role !== 'owner') {
      return res.status(403).json({ error: 'Apenas o proprietário pode alterar papéis.' });
    }
    if (role === 'owner') {
      return res.status(403).json({ error: 'Transferência de propriedade não é permitida por aqui.' });
    }
  }

  const newDisplayName = display_name || target.display_name;
  const newRole = (role && req.user.role === 'owner') ? role : target.role;
  const newHash = password ? bcrypt.hashSync(password, 12) : target.password_hash;

  await run('UPDATE users SET display_name = ?, role = ?, password_hash = ? WHERE id = ?',
    newDisplayName, newRole, newHash, targetId);

  await logAction(req.user.id, 'EDITOU_USUARIO', String(targetId));
  res.json({ ok: true });
}));

router.delete('/:id', requireRole('admin'), asyncRoute(async (req, res) => {
  const targetId = Number(req.params.id);
  const target = await get('SELECT * FROM users WHERE id = ?', targetId);
  if (!target) return res.status(404).json({ error: 'Usuário não encontrado.' });
  if (target.role === 'owner') {
    return res.status(403).json({ error: 'O proprietário não pode ser excluído.' });
  }
  if (target.role === 'admin' && req.user.role !== 'owner') {
    return res.status(403).json({ error: 'Apenas o proprietário pode excluir administradores.' });
  }
  await run('DELETE FROM users WHERE id = ?', targetId);
  await logAction(req.user.id, 'EXCLUIU_USUARIO', String(targetId));
  res.json({ ok: true });
}));

module.exports = router;
