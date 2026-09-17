const path = require('path');
const fs = require('fs');
const { Pool, types } = require('pg');

if (!process.env.DATABASE_URL) {
  console.error('ERRO: defina DATABASE_URL (veja o .env.example) antes de iniciar o servidor.');
  console.error('Crie um banco gratuito em https://neon.tech — veja o README para o passo a passo.');
  process.exit(1);
}

// Por padrão o driver do Postgres devolve COUNT(*)/bigint como string (pra não
// perder precisão em números gigantes). Aqui isso nunca acontece, então
// convertemos direto pra number pra não quebrar comparações tipo "row.count === 0".
types.setTypeParser(20, (val) => parseInt(val, 10));

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false },
});

// Converte os "?" (estilo SQLite, usado em todo o resto do código) para os
// "$1, $2, ..." que o Postgres espera, e traduz a única função de data do
// SQLite que era usada direto dentro de uma query (datetime('now')).
function toPgSql(sql) {
  let i = 0;
  return sql
    .replace(/datetime\('now'\)/g, "TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')")
    .replace(/\?/g, () => `$${++i}`);
}

async function get(sql, ...args) {
  const res = await pool.query(toPgSql(sql), args);
  return res.rows[0];
}

async function all(sql, ...args) {
  const res = await pool.query(toPgSql(sql), args);
  return res.rows;
}

// Emula o "info.lastInsertRowid" que o resto do código já espera: toda tabela usada
// com INSERT aqui tem uma coluna "id", então acrescentamos RETURNING id
// automaticamente quando a query for um INSERT que ainda não pediu retorno.
async function run(sql, ...args) {
  let finalSql = toPgSql(sql);
  const isInsert = /^\s*insert/i.test(sql) && !/returning/i.test(sql);
  if (isInsert) finalSql += ' RETURNING id';
  const res = await pool.query(finalSql, args);
  return {
    lastInsertRowid: isInsert && res.rows[0] ? res.rows[0].id : undefined,
    changes: res.rowCount,
  };
}

// Gera o próximo ID público (ex: ATV-001, TRB-002) por tipo de publicação.
async function nextPublicId(prefix) {
  const row = await get(
    `SELECT public_id FROM activities WHERE public_id LIKE ? ORDER BY id DESC LIMIT 1`,
    prefix + '-%'
  );
  let n = 1;
  if (row) {
    const parts = row.public_id.split('-');
    n = parseInt(parts[1], 10) + 1;
  }
  return `${prefix}-${String(n).padStart(3, '0')}`;
}

async function initSchema() {
  const schema = fs.readFileSync(path.join(__dirname, 'schema.sql'), 'utf8');
  await pool.query(schema);
}

module.exports = { pool, get, all, run, nextPublicId, initSchema };
