const express = require('express');
const { all, run } = require('../db');
const { requireAuth, requireRole, asyncRoute } = require('../middleware/auth');

const router = express.Router();
router.use(requireAuth);

// Carrega mensagens mais antigas que "before" (paginação / carregamento progressivo).
router.get('/', asyncRoute(async (req, res) => {
  const before = req.query.before ? req.query.before : new Date().toISOString();
  const limit = 30;
  const rows = await all(`
    SELECT m.id, m.content, m.created_at, m.deleted, u.id as user_id, u.display_name, u.role
    FROM messages m JOIN users u ON u.id = m.user_id
    WHERE m.created_at < ?
    ORDER BY m.created_at DESC
    LIMIT ?
  `, before, limit);
  res.json({ messages: rows.reverse() });
}));

// Moderação: administradores e o proprietário podem apagar mensagens.
router.delete('/:id', requireRole('admin'), asyncRoute(async (req, res) => {
  const id = Number(req.params.id);
  await run('UPDATE messages SET deleted = 1, content = ? WHERE id = ?', '[mensagem removida]', id);
  await run('INSERT INTO logs (user_id, action, target_id) VALUES (?, ?, ?)', req.user.id, 'APAGOU_MENSAGEM', String(id));
  res.json({ ok: true });
}));

module.exports = router;
