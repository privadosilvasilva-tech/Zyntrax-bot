const RANK = { aluno: 0, support: 1, admin: 2, owner: 3 };
const TYPE_LABEL = {
  ATIVIDADE: '📚 Atividade', TRABALHO: '📝 Trabalho', 'TAREFA DE CASA': '🏠 Tarefa de casa',
  AVISO: '📢 Aviso', PROVA: '📖 Prova', MATERIAL: '📎 Material',
};
const STATUS_LABEL = {
  PENDENTE: '🟢 Pendente', PROXIMO: '🟡 Prazo próximo', AMANHA: '🔴 Entrega amanhã',
  ENCERRADO: '⚫ Prazo encerrado', CONCLUIDA: '✅ Concluída',
};
const TAG_LABEL = { owner: '👑 PROPRIETÁRIO', admin: '🛠️ ADMINISTRADOR', support: '🆘 SUPORTE', aluno: '👤 ALUNO' };

let state = { user: null, activities: [], socket: null, oldestMsgDate: null, calMonth: new Date() };

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

async function api(path, opts = {}) {
  const res = await fetch('/api' + path, {
    method: opts.method || 'GET',
    headers: opts.body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    body: opts.body instanceof FormData ? opts.body : (opts.body ? JSON.stringify(opts.body) : undefined),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Erro inesperado.');
  return data;
}

/* ---------------- Tema ---------------- */
function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  $('#themeToggle').textContent = t === 'dark' ? '☀️ Modo claro' : '🌙 Modo escuro';
  localStorage.setItem('theme', t);
}
$('#themeToggle').addEventListener('click', () => {
  const cur = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  applyTheme(cur);
});
applyTheme(localStorage.getItem('theme') || 'light');

/* ---------------- Música de fundo (YouTube, toca em loop) ---------------- */
const BGM_VIDEO_ID = 'g2o3CZaVVCo';
const musicBtn = $('#musicToggle');
let bgmPlayer = null;
let bgmReady = false;

function setMusicUI(on) {
  musicBtn.textContent = on ? '🔊' : '🔈';
  musicBtn.classList.toggle('on', on);
}

// A API do YouTube chama esta função global assim que termina de carregar.
window.onYouTubeIframeAPIReady = function () {
  bgmPlayer = new YT.Player('bgmPlayer', {
    videoId: BGM_VIDEO_ID,
    playerVars: {
      autoplay: 1,
      mute: 1, // navegadores só permitem autoplay se começar mudo
      loop: 1,
      playlist: BGM_VIDEO_ID, // necessário para o loop=1 funcionar num vídeo único
      controls: 0,
      disablekb: 1,
      fs: 0,
      modestbranding: 1,
    },
    events: {
      onReady: (e) => {
        bgmReady = true;
        e.target.playVideo();
        const wantsSound = localStorage.getItem('musicOn') === '1';
        if (wantsSound) { e.target.unMute(); }
        setMusicUI(wantsSound);
      },
      // Garantia extra: se por algum motivo o vídeo terminar, reinicia do zero.
      onStateChange: (e) => {
        if (e.data === YT.PlayerState.ENDED) {
          e.target.seekTo(0);
          e.target.playVideo();
        }
      },
    },
  });
};

musicBtn.addEventListener('click', () => {
  if (!bgmReady || !bgmPlayer) return;
  const willBeOn = musicBtn.textContent === '🔈';
  if (willBeOn) bgmPlayer.unMute(); else bgmPlayer.mute();
  localStorage.setItem('musicOn', willBeOn ? '1' : '0');
  setMusicUI(willBeOn);
});

/* ---------------- Login / sessão ---------------- */
api('/settings').then(s => {
  $('#turmaNome').textContent = s.nome_da_turma;
  $('#turmaNomeSide').textContent = s.nome_da_turma;
}).catch(() => {});

$('#loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  $('#loginError').hidden = true;
  try {
    const { user } = await api('/auth/login', {
      method: 'POST',
      body: { username: $('#loginUsername').value, password: $('#loginPassword').value },
    });
    startApp(user);
  } catch (err) {
    $('#loginError').textContent = err.message;
    $('#loginError').hidden = false;
  }
});

$('#logoutBtn').addEventListener('click', async () => {
  await api('/auth/logout', { method: 'POST' }).catch(() => {});
  location.reload();
});

$('#setupForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  $('#setupError').hidden = true;
  try {
    const { user } = await api('/auth/setup', {
      method: 'POST',
      body: {
        display_name: $('#setupDisplayName').value,
        username: $('#setupUsername').value,
        password: $('#setupPassword').value,
      },
    });
    $('#setupScreen').hidden = true;
    startApp(user);
  } catch (err) {
    $('#setupError').textContent = err.message;
    $('#setupError').hidden = false;
  }
});

api('/auth/setup-status').then(({ needsSetup }) => {
  if (needsSetup) { $('#setupScreen').hidden = false; return; }
  api('/auth/me').then(({ user }) => startApp(user)).catch(() => { $('#loginScreen').hidden = false; });
}).catch(() => {
  api('/auth/me').then(({ user }) => startApp(user)).catch(() => { $('#loginScreen').hidden = false; });
});

function startApp(user) {
  state.user = user;
  $('#loginScreen').hidden = true;
  $('#app').hidden = false;
  $('#userName').textContent = user.display_name;
  $('#userTag').textContent = TAG_LABEL[user.role];
  $('#userTag').className = 'tag tag-' + user.role;

  $$('.nav-item[data-role-min]').forEach(el => {
    const min = el.getAttribute('data-role-min');
    el.style.display = RANK[user.role] >= RANK[min] ? '' : 'none';
  });

  connectSocket();
  goTo('dashboard');
  loadActivities();
}

/* ---------------- Navegação ---------------- */
function goTo(view) {
  $$('.view').forEach(v => v.hidden = true);
  $('#view-' + view).hidden = false;
  $$('.nav-item[data-view]').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  const titles = { dashboard: 'Início', atividades: 'Atividades', calendario: 'Calendário', chat: 'Chat', avisos: 'Avisos', perfil: 'Meu perfil', admin: 'Painel administrativo', owner: 'Painel exclusivo do proprietário' };
  $('#viewTitle').textContent = titles[view] || '';
  const renderers = { dashboard: renderDashboard, atividades: renderAtividades, calendario: renderCalendario, chat: renderChat, avisos: renderAvisos, perfil: renderPerfil, admin: renderAdmin, owner: renderOwner };
  if (renderers[view]) renderers[view]();
}
$$('.nav-item[data-view]').forEach(btn => btn.addEventListener('click', () => goTo(btn.dataset.view)));

/* ---------------- Atividades (dados) ---------------- */
async function loadActivities() {
  const { activities } = await api('/activities');
  state.activities = activities;
}

function statusBadge(status) {
  return `<span class="status-badge status-${status}">${STATUS_LABEL[status]}</span>`;
}

function activityCard(a) {
  const canManage = RANK[state.user.role] >= RANK['admin'] || (state.user.role === 'support' && a.type === 'AVISO');
  return `
  <div class="activity-card">
    <div class="activity-top">
      <div>
        <div class="activity-id">${a.public_id} · ${TYPE_LABEL[a.type] || a.type}</div>
        <div class="activity-title">${escapeHtml(a.title)}</div>
      </div>
      ${statusBadge(a.status)}
    </div>
    <div class="activity-meta">
      ${a.subject ? `<span>📘 ${escapeHtml(a.subject)}</span>` : ''}
      ${a.teacher ? `<span>👨‍🏫 ${escapeHtml(a.teacher)}</span>` : ''}
      ${a.due_date ? `<span>⏰ Entrega: ${formatDate(a.due_date)}${a.due_time ? ' às ' + a.due_time : ''}</span>` : ''}
      <span>✍️ ${escapeHtml(a.author_name)}</span>
    </div>
    ${a.description ? `<div class="activity-desc">${escapeHtml(a.description)}</div>` : ''}
    ${a.file_path ? `<div><a href="${a.file_path}" target="_blank">📎 Ver anexo</a></div>` : ''}
    ${canManage ? `
      <div class="activity-actions">
        <button class="btn btn-ghost" onclick="openActivityModal(${a.id})">Editar</button>
        ${RANK[state.user.role] >= RANK['admin'] ? `<button class="btn btn-danger" onclick="deleteActivity(${a.id})">Excluir</button>` : ''}
      </div>` : ''}
  </div>`;
}

function escapeHtml(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }
function formatDate(iso) { const [y, m, d] = iso.split('-'); return `${d}/${m}/${y}`; }

/* ---------------- Dashboard ---------------- */
function renderDashboard() {
  const pend = state.activities.filter(a => a.status !== 'ENCERRADO' && a.status !== 'CONCLUIDA');
  const amanha = state.activities.filter(a => a.status === 'AMANHA');
  const proxima = [...pend].sort((a, b) => (a.due_date || '9999').localeCompare(b.due_date || '9999'))[0];

  $('#view-dashboard').innerHTML = `
    <p style="font-size:16px;margin-bottom:20px;">Olá, ${escapeHtml(state.user.display_name)}! 👋</p>
    <div class="stat-grid">
      <div class="stat-card"><div class="stat-label">Atividades pendentes</div><div class="stat-num">${pend.length}</div></div>
      <div class="stat-card"><div class="stat-label">Entregas amanhã</div><div class="stat-num">${amanha.length}</div></div>
      <div class="stat-card"><div class="stat-label">Próxima atividade</div><div class="stat-num" style="font-size:16px;">${proxima ? escapeHtml(proxima.title) : '—'}</div><div class="stat-label">${proxima && proxima.due_date ? formatDate(proxima.due_date) : ''}</div></div>
    </div>
    <div class="section-title">Acesso rápido</div>
    <div class="quick-links">
      <button class="quick-link" onclick="goTo('atividades')"><span>📚</span>Atividades</button>
      <button class="quick-link" onclick="goTo('calendario')"><span>📅</span>Calendário</button>
      <button class="quick-link" onclick="goTo('chat')"><span>💬</span>Chat</button>
      <button class="quick-link" onclick="goTo('avisos')"><span>📢</span>Avisos</button>
      <button class="quick-link" onclick="goTo('perfil')"><span>👤</span>Meu perfil</button>
    </div>
    <div class="section-title">Em destaque</div>
    <div class="activity-list">
      ${pend.slice(0, 5).map(activityCard).join('') || '<div class="empty-state">Nenhuma atividade pendente. 🎉</div>'}
    </div>
  `;
}

/* ---------------- Atividades (view) ---------------- */
let atividadesFilter = 'TODOS';
function renderAtividades() {
  const canCreate = RANK[state.user.role] >= RANK['support'];
  const list = atividadesFilter === 'TODOS' ? state.activities : state.activities.filter(a => a.type === atividadesFilter);
  $('#view-atividades').innerHTML = `
    ${canCreate ? `<div style="margin-bottom:16px;"><button class="btn btn-primary" onclick="openActivityModal()">+ Nova publicação</button></div>` : ''}
    <div class="filters">
      ${['TODOS', ...Object.keys(TYPE_LABEL)].map(t => `<button class="filter-chip ${atividadesFilter === t ? 'active' : ''}" data-filter="${t}">${t === 'TODOS' ? 'Todos' : TYPE_LABEL[t]}</button>`).join('')}
    </div>
    <div class="activity-list">${list.map(activityCard).join('') || '<div class="empty-state">Nada por aqui ainda.</div>'}</div>
  `;
  $$('.filter-chip').forEach(c => c.addEventListener('click', () => { atividadesFilter = c.dataset.filter; renderAtividades(); }));
}

function renderAvisos() {
  const list = state.activities.filter(a => a.type === 'AVISO');
  $('#view-avisos').innerHTML = `
    ${RANK[state.user.role] >= RANK['support'] ? `<div style="margin-bottom:16px;"><button class="btn btn-primary" onclick="openActivityModal(null,'AVISO')">+ Novo aviso</button></div>` : ''}
    <div class="activity-list">${list.map(activityCard).join('') || '<div class="empty-state">Nenhum aviso publicado ainda.</div>'}</div>
  `;
}

window.deleteActivity = async function (id) {
  if (!confirm('Excluir esta publicação?')) return;
  await api('/activities/' + id, { method: 'DELETE' });
  await loadActivities();
  renderAtividades();
};

window.openActivityModal = function (id, forcedType) {
  const existing = id ? state.activities.find(a => a.id === id) : null;
  const typeOptions = Object.keys(TYPE_LABEL).map(t => `<option value="${t}" ${(existing?.type || forcedType) === t ? 'selected' : ''}>${TYPE_LABEL[t]}</option>`).join('');
  showModal(`
    <h3>${existing ? 'Editar publicação' : 'Nova publicação'}</h3>
    <form id="activityForm">
      <div class="field"><label>Título</label><input name="title" required value="${existing ? escapeHtml(existing.title) : ''}" /></div>
      <div class="field-row">
        <div class="field"><label>Tipo</label><select name="type" ${forcedType ? 'disabled' : ''}>${typeOptions}</select></div>
        <div class="field"><label>Disciplina</label><input name="subject" value="${existing ? escapeHtml(existing.subject || '') : ''}" /></div>
      </div>
      <div class="field"><label>Professor(a)</label><input name="teacher" value="${existing ? escapeHtml(existing.teacher || '') : ''}" /></div>
      <div class="field"><label>Descrição</label><textarea name="description" rows="3">${existing ? escapeHtml(existing.description || '') : ''}</textarea></div>
      <div class="field-row">
        <div class="field"><label>Data de entrega</label><input type="date" name="due_date" value="${existing?.due_date || ''}" /></div>
        <div class="field"><label>Horário limite</label><input type="time" name="due_time" value="${existing?.due_time || ''}" /></div>
      </div>
      <div class="field"><label>Anexo (opcional)</label><input type="file" name="file" /></div>
      <div class="modal-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
        <button type="submit" class="btn btn-primary">${existing ? 'Salvar' : 'Publicar'}</button>
      </div>
    </form>
  `);
  $('#activityForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    if (forcedType) fd.set('type', forcedType);
    try {
      if (existing) await api('/activities/' + existing.id, { method: 'PUT', body: fd });
      else await api('/activities', { method: 'POST', body: fd });
      closeModal();
      await loadActivities();
      renderAtividades();
      renderDashboard();
    } catch (err) { alert(err.message); }
  });
};

/* ---------------- Calendário ---------------- */
function renderCalendario() {
  const month = state.calMonth;
  const y = month.getFullYear(), m = month.getMonth();
  const first = new Date(y, m, 1);
  const daysInMonth = new Date(y, m + 1, 0).getDate();
  const startWeekday = first.getDay();
  const monthName = month.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });

  const dueMap = {};
  state.activities.forEach(a => { if (a.due_date) (dueMap[a.due_date] = dueMap[a.due_date] || []).push(a); });

  let cells = '';
  for (let i = 0; i < startWeekday; i++) cells += `<div class="cal-day empty"></div>`;
  for (let d = 1; d <= daysInMonth; d++) {
    const iso = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const items = dueMap[iso] || [];
    cells += `<div class="cal-day ${items.length ? 'has-due' : ''}" onclick='showDayModal(${JSON.stringify(iso)})'>
      <div class="day-num">${d}</div>
      ${items.slice(0, 3).map(() => '<span class="dot"></span>').join('')}
    </div>`;
  }

  $('#view-calendario').innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
      <button class="btn btn-ghost" onclick="shiftMonth(-1)">← Anterior</button>
      <strong style="text-transform:capitalize;">${monthName}</strong>
      <button class="btn btn-ghost" onclick="shiftMonth(1)">Próximo →</button>
    </div>
    <div class="calendar-grid">
      ${['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'].map(d => `<div class="cal-head">${d}</div>`).join('')}
      ${cells}
    </div>
  `;
}
window.shiftMonth = function (delta) {
  state.calMonth = new Date(state.calMonth.getFullYear(), state.calMonth.getMonth() + delta, 1);
  renderCalendario();
};
window.showDayModal = function (iso) {
  const items = state.activities.filter(a => a.due_date === iso);
  showModal(`<h3>${formatDate(iso)}</h3><div class="activity-list">${items.map(activityCard).join('') || '<p class="empty-state">Nada para entregar neste dia.</p>'}</div>`);
};

/* ---------------- Chat ---------------- */
function connectSocket() {
  state.socket = io();
  state.socket.on('chat:new', (msg) => appendMessage(msg, true));
}
async function renderChat() {
  $('#view-chat').innerHTML = `
    <div class="chat-wrap">
      <div class="chat-messages" id="chatMessages">
        <button class="chat-load-more" id="loadMoreBtn">Carregar mensagens anteriores</button>
      </div>
      <div class="chat-input-bar">
        <input type="text" id="chatInput" placeholder="Escreva uma mensagem..." maxlength="2000" />
        <button class="btn btn-primary" id="chatSendBtn">Enviar</button>
      </div>
    </div>
  `;
  await loadOlderMessages(true);
  $('#loadMoreBtn').addEventListener('click', () => loadOlderMessages(false));
  const send = async () => {
    const input = $('#chatInput');
    if (!input.value.trim()) return;
    state.socket.emit('chat:send', input.value.trim());
    input.value = '';
  };
  $('#chatSendBtn').addEventListener('click', send);
  $('#chatInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
}

async function loadOlderMessages(initial) {
  const before = state.oldestMsgDate || new Date().toISOString();
  const { messages } = await api('/chat?before=' + encodeURIComponent(before));
  if (messages.length) state.oldestMsgDate = messages[0].created_at;
  const box = $('#chatMessages');
  const scrollAnchor = box.scrollHeight;
  messages.forEach(m => appendMessage(m, false, true));
  if (initial) box.scrollTop = box.scrollHeight;
  else box.scrollTop = box.scrollHeight - scrollAnchor;
  if (messages.length < 30) $('#loadMoreBtn').style.display = 'none';
}

function appendMessage(m, scrollDown, prepend) {
  const box = $('#chatMessages');
  if (!box) return;
  const mine = m.user_id === state.user.id;
  const el = document.createElement('div');
  el.className = 'chat-msg' + (mine ? ' mine' : '');
  const time = new Date(m.created_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  el.innerHTML = `
    <div class="chat-msg-head">
      <span class="tag tag-${m.role}" style="font-size:10px;">${TAG_LABEL[m.role]}</span>
      <span class="chat-msg-name">${escapeHtml(m.display_name)}</span>
      <span class="chat-msg-time">${time}</span>
    </div>
    <div class="chat-bubble">${escapeHtml(m.content)}</div>
  `;
  if (prepend) box.insertBefore(el, box.firstChild.nextSibling);
  else box.appendChild(el);
  if (scrollDown) box.scrollTop = box.scrollHeight;
}

/* ---------------- Perfil ---------------- */
function renderPerfil() {
  $('#view-perfil').innerHTML = `
    <div class="table-wrap" style="padding:20px;max-width:420px;">
      <p><strong>Nome:</strong> ${escapeHtml(state.user.display_name)}</p>
      <p><strong>Usuário:</strong> ${escapeHtml(state.user.username)}</p>
      <p><strong>Papel:</strong> <span class="tag tag-${state.user.role}">${TAG_LABEL[state.user.role]}</span></p>
      <hr style="border-color:var(--border);margin:16px 0;">
      <form id="pwForm">
        <div class="field"><label>Nova senha</label><input type="password" name="password" minlength="4" required /></div>
        <button class="btn btn-primary">Alterar minha senha</button>
      </form>
    </div>
  `;
  $('#pwForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const password = new FormData(e.target).get('password');
    try {
      await api('/users/' + state.user.id, { method: 'PUT', body: { password } });
      alert('Senha alterada com sucesso.');
      e.target.reset();
    } catch (err) { alert(err.message); }
  });
}

/* ---------------- Admin ---------------- */
let adminTab = 'usuarios';
async function renderAdmin() {
  $('#view-admin').innerHTML = `
    <div class="admin-tabs">
      <button class="admin-tab ${adminTab === 'usuarios' ? 'active' : ''}" data-tab="usuarios">👥 Usuários</button>
      <button class="admin-tab ${adminTab === 'atividades' ? 'active' : ''}" data-tab="atividades">📚 Atividades</button>
    </div>
    <div id="adminContent"></div>
  `;
  $$('.admin-tab').forEach(t => t.addEventListener('click', () => { adminTab = t.dataset.tab; renderAdmin(); }));
  if (adminTab === 'usuarios') await renderAdminUsers();
  else renderAdminAtividades();
}

async function renderAdminUsers() {
  const { users } = await api('/users');
  const canManage = RANK[state.user.role] >= RANK['admin'];
  $('#adminContent').innerHTML = `
    ${canManage ? `<div style="margin-bottom:14px;"><button class="btn btn-primary" onclick="openUserModal()">+ Criar usuário</button></div>` : '<p class="empty-state" style="padding:10px 0;">Você pode visualizar os usuários, mas apenas administradores podem criar ou editar contas.</p>'}
    <div class="table-wrap"><table>
      <thead><tr><th>Nome</th><th>Usuário</th><th>Papel</th><th></th></tr></thead>
      <tbody>
        ${users.map(u => `<tr>
          <td>${escapeHtml(u.display_name)}</td>
          <td>${escapeHtml(u.username)}</td>
          <td><span class="tag tag-${u.role}">${TAG_LABEL[u.role]}</span></td>
          <td>${canManage && u.role !== 'owner' ? `
            <button class="btn btn-ghost" onclick='openUserModal(${JSON.stringify(u).replace(/'/g, "&apos;")})'>Editar</button>
            <button class="btn btn-danger" onclick="deleteUser(${u.id})">Excluir</button>` : ''}
          </td>
        </tr>`).join('')}
      </tbody>
    </table></div>
  `;
}

function renderAdminAtividades() {
  $('#adminContent').innerHTML = `
    <div style="margin-bottom:14px;"><button class="btn btn-primary" onclick="openActivityModal()">+ Nova publicação</button></div>
    <div class="activity-list">${state.activities.map(activityCard).join('') || '<div class="empty-state">Nada publicado ainda.</div>'}</div>
  `;
}

window.deleteUser = async function (id) {
  if (!confirm('Excluir este usuário?')) return;
  try { await api('/users/' + id, { method: 'DELETE' }); renderAdminUsers(); }
  catch (err) { alert(err.message); }
};

window.openUserModal = function (user) {
  const isOwnerActing = state.user.role === 'owner';
  const roleOptions = ['aluno', 'support', 'admin'].concat(isOwnerActing ? [] : []).map(r =>
    `<option value="${r}" ${user?.role === r ? 'selected' : ''}>${TAG_LABEL[r]}</option>`).join('');
  showModal(`
    <h3>${user ? 'Editar usuário' : 'Criar usuário'}</h3>
    <form id="userForm">
      <div class="field"><label>Nome de exibição</label><input name="display_name" required value="${user ? escapeHtml(user.display_name) : ''}" /></div>
      ${!user ? `<div class="field"><label>Usuário (login)</label><input name="username" required /></div>` : ''}
      <div class="field"><label>${user ? 'Nova senha (deixe em branco para manter)' : 'Senha'}</label><input type="password" name="password" ${user ? '' : 'required'} minlength="4" /></div>
      <div class="field"><label>Papel</label><select name="role" ${!isOwnerActing ? 'disabled' : ''}>${roleOptions}</select></div>
      ${!isOwnerActing ? '<p style="font-size:12px;color:var(--ink-soft);">Só o proprietário pode definir o papel/permissão.</p>' : ''}
      <div class="modal-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
        <button type="submit" class="btn btn-primary">Salvar</button>
      </div>
    </form>
  `);
  $('#userForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    if (!body.password) delete body.password;
    try {
      if (user) await api('/users/' + user.id, { method: 'PUT', body });
      else await api('/users', { method: 'POST', body });
      closeModal();
      renderAdminUsers();
    } catch (err) { alert(err.message); }
  });
};

/* ---------------- Painel do proprietário ---------------- */
async function renderOwner() {
  const { logs } = await api('/logs');
  $('#view-owner').innerHTML = `
    <div class="owner-banner">
      <h3>👑 Painel exclusivo do proprietário — BY ANDRY</h3>
      <p>Registros administrativos e controle geral do sistema.</p>
    </div>
    <div class="section-title">Últimas ações registradas</div>
    <div class="table-wrap"><table>
      <thead><tr><th>Quando</th><th>Quem</th><th>Ação</th><th>Referência</th></tr></thead>
      <tbody>
        ${logs.map(l => `<tr>
          <td>${new Date(l.created_at).toLocaleString('pt-BR')}</td>
          <td>${l.display_name ? escapeHtml(l.display_name) + ' ' + (TAG_LABEL[l.role] || '') : '—'}</td>
          <td>${l.action}</td>
          <td>${l.target_id || ''}</td>
        </tr>`).join('') || '<tr><td colspan="4" class="empty-state">Sem registros ainda.</td></tr>'}
      </tbody>
    </table></div>
  `;
}

/* ---------------- Modal genérico ---------------- */
function showModal(html) {
  $('#modalBox').innerHTML = html;
  $('#modalBackdrop').hidden = false;
}
window.closeModal = function () { $('#modalBackdrop').hidden = true; };
$('#modalBackdrop').addEventListener('click', (e) => { if (e.target.id === 'modalBackdrop') closeModal(); });
