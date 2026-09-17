// Camada só de efeitos visuais (ripple nos cliques + reanimação de troca de
// tela). Não mexe em nenhuma lógica de dados do app.js — só observa o DOM.
(function () {
  function addRipple(e, el) {
    const rect = el.getBoundingClientRect();
    const ripple = document.createElement('span');
    const size = Math.max(rect.width, rect.height);
    ripple.className = 'ripple';
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
    ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
    const prevPosition = getComputedStyle(el).position;
    if (prevPosition === 'static') el.style.position = 'relative';
    el.style.overflow = el.style.overflow || 'hidden';
    el.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
  }

  document.addEventListener('click', (e) => {
    const el = e.target.closest('.btn, .nav-item, .filter-chip, .admin-tab, .quick-link, .stat-card');
    if (el) addRipple(e, el);
  });

  // Reanima a view toda vez que ela deixa de ficar "hidden" (troca de aba).
  document.querySelectorAll('.view').forEach((view) => {
    const observer = new MutationObserver(() => {
      if (!view.hasAttribute('hidden')) {
        view.classList.remove('anim-in');
        // força reflow pra reiniciar a animação mesmo se a classe já existisse
        void view.offsetWidth;
        view.classList.add('anim-in');
      }
    });
    observer.observe(view, { attributes: true, attributeFilter: ['hidden'] });
  });
})();
