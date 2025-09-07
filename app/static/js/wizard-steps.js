/* wizard.js */
function attachSortableLists(root = document) {
  root.querySelectorAll('.wizard-steps, .bundle-steps').forEach(container => {
    if (container.dataset.sortableAttached) return;

    new Sortable(container, {
      animation: 150,
      handle: '.drag',
      ghostClass: 'opacity-50',   // was dragClass
      onEnd({ to }) {
        const ids = [...to.children].map(li => Number(li.dataset.id));
        fetch(to.dataset.reorderUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(ids)
        });
      }
    });
    container.dataset.sortableAttached = '1';
  });
}

// Attach Next-button gating that requires an interaction inside step content
function attachInteractionGating(root = document) {
  const next = root.querySelector('#next-btn');
  if (!next) return;
  if (next.dataset.interactionGatingAttached === '1') return;
  next.dataset.interactionGatingAttached = '1';

  // Only activate if the server rendered this step as requiring interaction
  if (next.dataset.disabled === '1') {
    const content = root.querySelector('#wizard-wrapper .prose');

    // 1) Hard-disable HTMX by removing hx-get temporarily
    const savedHxGet = next.getAttribute('hx-get');
    if (savedHxGet != null) {
      next.dataset.savedHxGet = savedHxGet;
      next.removeAttribute('hx-get');
    }

    // 2) Block clicks & keyboard activation at capture phase (before htmx)
    function clickBlocker(e) {
      if (next.dataset.disabled === '1') {
        e.preventDefault();
        e.stopPropagation();
      }
    }
    function keyBlocker(e) {
      if (next.dataset.disabled === '1' && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        e.stopPropagation();
      }
    }
    next.addEventListener('click', clickBlocker, true);  // capture
    next.addEventListener('keydown', keyBlocker, true);  // capture

    function enable() {
      // Restore HTMX capability first
      if (next.dataset.savedHxGet != null) {
        next.setAttribute('hx-get', next.dataset.savedHxGet);
        delete next.dataset.savedHxGet;
      }

      next.dataset.disabled = '0';
      next.removeAttribute('aria-disabled');
      next.removeAttribute('tabindex');
      next.style.pointerEvents = '';
      next.style.opacity = '';
      next.style.cursor = '';

      // Remove blockers & listeners
      next.removeEventListener('click', clickBlocker, true);
      next.removeEventListener('keydown', keyBlocker, true);
      if (content) content.removeEventListener('click', handler, true);
    }

    function handler(ev) {
      const t = ev.target;
      if (!t) return;
      if (t.closest && t.closest('a,button') !== null) enable();
    }

    // Listen for any click within the content that bubbles/captures from links/buttons
    if (content) content.addEventListener('click', handler, true);

    // 3) Apply disabled affordance & interaction lock
    next.setAttribute('tabindex', '-1');
    // Keep pointer events so the tooltip is visible while disabled
    next.style.opacity = '0.6';
    next.style.cursor = 'not-allowed';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  attachSortableLists();
  attachInteractionGating();
});
document.body.addEventListener('htmx:load', e => {
  attachSortableLists(e.target);
  attachInteractionGating(e.target);
});
