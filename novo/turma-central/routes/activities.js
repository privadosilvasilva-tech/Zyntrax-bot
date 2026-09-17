const express = require('express');
const path = require('path');
const crypto = require('crypto');
const multer = require('multer');
const { all, get, run, nextPublicId } = require('../db');
const { requireAuth, requireRole, asyncRoute } = require('../middleware/auth');

const router = express.Router();

const TYPE_PREFIX = {
  ATIVIDADE: 'ATV',
  TRABALHO: 'TRB',
  'TAREFA DE CASA': 'TC',
  AVISO: 'AVS',
  PROVA: 'PRV',
  MATERIAL: 'MAT',
};

const storage = multer.diskStorage({
  destination: path.join(__dirname, '..', 'public', 'uploads'),
  filename: (req, file, cb) => {
    const safeExt = path.extname(file.originalname).slice(0, 10).replace(/[^a-zA-Z0-9.]/g, '');
    cb(null, `${Date.now()}-${crypto.randomBytes(6).toString('hex')}${safeExt}`);
  },
});
const upload = multer({
  storage,
  limits: { fileSize: 15 * 1024 * 1024 }, // 15 MB
  fileFilter: (req, file, cb) => {
    const allowed = /\.(pdf|docx?|xlsx?|pptx?|png|jpe?g|gif|webp|zip|txt)$/i;
    if (!allowed.test(file.originalname)) return cb(new Error('Tipo de arquivo não permitido.'));
    cb(null, true);
  },
});

function computeStatus(a) {
  if (a.manual_status) return a.manual_status;
  if (!a.due_date) return 'PENDENTE';
  const dueStr = a.due_time ? `${a.due_date}T${a.due_time}` : `${a.due_date}T23:59:59`;
  const due = new Date(dueStr);
  const now = new Date();
  const diffMs = due - now;
  const diffH = diffMs / (1000 * 60 * 60);
  if (diffMs < 0) return 'ENCERRADO';
  if (diffH <= 24) return 'AMANHA';
  if (diffH <= 72) return 'PROXIMO';
  return 'PENDENTE';
}

router.use(requireAuth);

router.get('/', asyncRoute(async (req, res) => {
  const rows = await all(`
    SELECT a.*, u.display_name as author_name, u.role as author_role
    FROM activities a JOIN users u ON u.id = a.author_id
    ORDER BY a.due_date IS NULL, a.due_date ASC, a.id DESC
  `);
  const withStatus = rows.map(a => ({ ...a, status: computeStatus(a) }));
  res.json({ activities: withStatus });
}));

router.post('/', requireRole('support'), upload.single('file'), asyncRoute(async (req, res) => {
  const { title, subject, teacher, description, type, due_date, due_time } = req.body || {};
  if (!title || !type) return res.status(400).json({ error: 'Título e tipo são obrigatórios.' });

  // Suporte só pode publicar avisos.
  if (req.user.role === 'support' && type !== 'AVISO') {
    return res.status(403).json({ error: 'Suporte só pode publicar avisos.' });
  }

  const prefix = TYPE_PREFIX[type] || 'GEN';
  const publicId = await nextPublicId(prefix);
  const filePath = req.file ? `/uploads/${req.file.filename}` : null;

  const info = await run(`
    INSERT INTO activities (public_id, title, subject, teacher, description, type, due_date, due_time, file_path, author_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `, publicId, title, subject || null, teacher || null, description || null, type, due_date || null, due_time || null, filePath, req.user.id);

  await run('INSERT INTO logs (user_id, action, target_id) VALUES (?, ?, ?)', req.user.id, 'CRIOU_ATIVIDADE', publicId);

  res.status(201).json({ id: info.lastInsertRowid, public_id: publicId });
}));

router.put('/:id', requireRole('support'), upload.single('file'), asyncRoute(async (req, res) => {
  const id = Number(req.params.id);
  const existing = await get('SELECT * FROM activities WHERE id = ?', id);
  if (!existing) return res.status(404).json({ error: 'Publicação não encontrada.' });
  if (req.user.role === 'support' && existing.type !== 'AVISO') {
    return res.status(403).json({ error: 'Suporte só pode editar avisos.' });
  }

  const { title, subject, teacher, description, type, due_date, due_time, manual_status } = req.body || {};
  const filePath = req.file ? `/uploads/${req.file.filename}` : existing.file_path;

  await run(`
    UPDATE activities SET title=?, subject=?, teacher=?, description=?, type=?, due_date=?, due_time=?,
    file_path=?, manual_status=?, updated_at=datetime('now') WHERE id=?
  `,
    title || existing.title, subject ?? existing.subject, teacher ?? existing.teacher,
    description ?? existing.description, type || existing.type, due_date ?? existing.due_date,
    due_time ?? existing.due_time, filePath, manual_status ?? existing.manual_status, id
  );

  await run('INSERT INTO logs (user_id, action, target_id) VALUES (?, ?, ?)', req.user.id, 'EDITOU_ATIVIDADE', existing.public_id);

  res.json({ ok: true });
}));

router.delete('/:id', requireRole('admin'), asyncRoute(async (req, res) => {
  const id = Number(req.params.id);
  const existing = await get('SELECT * FROM activities WHERE id = ?', id);
  if (!existing) return res.status(404).json({ error: 'Publicação não encontrada.' });
  await run('DELETE FROM activities WHERE id = ?', id);
  await run('INSERT INTO logs (user_id, action, target_id) VALUES (?, ?, ?)', req.user.id, 'EXCLUIU_ATIVIDADE', existing.public_id);
  res.json({ ok: true });
}));

module.exports = router;
