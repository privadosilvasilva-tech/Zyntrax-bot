const express = require('express');
const { all } = require('../db');
const { requireAuth, requireRole, asyncRoute } = require('../middleware/auth');

const router = express.Router();
router.use(requireAuth, requireRole('admin'));

router.get('/', asyncRoute(async (req, res) => {
  const rows = await all(`
    SELECT l.id, l.action, l.target_id, l.created_at, u.display_name, u.role
    FROM logs l LEFT JOIN users u ON u.id = l.user_id
    ORDER BY l.id DESC LIMIT 200
  `);
  res.json({ logs: rows });
}));

module.exports = router;
