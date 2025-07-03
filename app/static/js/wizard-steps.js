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

document.addEventListener('DOMContentLoaded', () => attachSortableLists());
document.body.addEventListener('htmx:load', e => attachSortableLists(e.target));
