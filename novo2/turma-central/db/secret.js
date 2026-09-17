const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Gera (uma única vez) e reaproveita um segredo para assinar as sessões (JWT).
// Fica guardado em db/.jwt-secret, que nunca é enviado ao GitHub (.gitignore).
// Assim ninguém precisa configurar nada manualmente: o servidor cuida disso sozinho.
const SECRET_FILE = path.join(__dirname, '.jwt-secret');

function getJwtSecret() {
  if (process.env.JWT_SECRET) return process.env.JWT_SECRET; // permite sobrescrever se quiser
  if (fs.existsSync(SECRET_FILE)) {
    return fs.readFileSync(SECRET_FILE, 'utf8').trim();
  }
  const generated = crypto.randomBytes(48).toString('hex');
  fs.writeFileSync(SECRET_FILE, generated, { mode: 0o600 });
  return generated;
}

module.exports = { JWT_SECRET: getJwtSecret() };
