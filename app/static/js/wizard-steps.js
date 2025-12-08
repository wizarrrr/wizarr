/* wizard.js */

// Helper function to show toast notifications
function showToast(message, type = 'info') {
  // Check if there's a toast container, create if not
  let toastContainer = document.getElementById('toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.className = 'fixed top-4 right-4 z-50 space-y-2';
    document.body.appendChild(toastContainer);
  }

  // Create toast element
  const toast = document.createElement('div');
  const bgColor = type === 'error' ? 'bg-red-500' : type === 'success' ? 'bg-green-500' : 'bg-blue-500';
  toast.className = `${bgColor} text-white px-6 py-3 rounded-lg shadow-lg transition-opacity duration-300`;
  toast.textContent = message;

  toastContainer.appendChild(toast);

  // Auto-remove after 3 seconds
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function attachSortableLists(root = document) {
  root.querySelectorAll('.wizard-steps, .bundle-steps').forEach(container => {
    if (container.dataset.sortableAttached) return;

    // Check if this is a category-aware wizard steps list
    const isCategoryAware = container.classList.contains('wizard-steps') && container.dataset.category;
    const isBundleList = container.classList.contains('bundle-steps');

    const sortableConfig = {
      animation: 150,
      handle: '.drag',
      ghostClass: 'sortable-ghost',
      chosenClass: 'sortable-chosen',
      dragClass: 'sortable-drag',
      // Prevent empty state placeholder from being draggable
      filter: '.empty-state-item',
      // Add visual feedback for valid/invalid drop zones
      onStart(evt) {
        // Remove empty state placeholder from all containers when drag starts
        document.querySelectorAll('.wizard-steps .empty-state-item, .bundle-steps .empty-state-item').forEach(placeholder => {
          placeholder.style.display = 'none';
        });
      },
      onMove(evt) {
        if (isCategoryAware) {
          const fromServer = evt.from.dataset.server;
          const toServer = evt.to.dataset.server;
          const isValid = fromServer === toServer;

          // Add visual feedback to drop zone
          if (isValid) {
            evt.to.classList.add('bg-green-50', 'dark:bg-green-900/20', 'border-green-300', 'dark:border-green-700');
            evt.to.classList.remove('bg-red-50', 'dark:bg-red-900/20', 'border-red-300', 'dark:border-red-700');
          } else {
            evt.to.classList.add('bg-red-50', 'dark:bg-red-900/20', 'border-red-300', 'dark:border-red-700');
            evt.to.classList.remove('bg-green-50', 'dark:bg-green-900/20', 'border-green-300', 'dark:border-green-700');
          }

          return isValid;
        }
        if (isBundleList) {
          const fromBundle = evt.from.dataset.bundle;
          const toBundle = evt.to.dataset.bundle;
          const sameBundle = fromBundle === toBundle;
          const isValid = sameBundle;

          if (isValid) {
            evt.to.classList.add('bg-green-50', 'dark:bg-green-900/20', 'border-green-300', 'dark:border-green-700');
            evt.to.classList.remove('bg-red-50', 'dark:bg-red-900/20', 'border-red-300', 'dark:border-red-700');
          } else {
            evt.to.classList.add('bg-red-50', 'dark:bg-red-900/20', 'border-red-300', 'dark:border-red-700');
            evt.to.classList.remove('bg-green-50', 'dark:bg-green-900/20', 'border-green-300', 'dark:border-green-700');
          }

          return isValid;
        }
        return true;
      },
      onEnd(evt) {
        const { to, from, item } = evt;
        // Remove visual feedback classes
        to.classList.remove('bg-green-50', 'dark:bg-green-900/20', 'border-green-300', 'dark:border-green-700');
        to.classList.remove('bg-red-50', 'dark:bg-red-900/20', 'border-red-300', 'dark:border-red-700');
        from.classList.remove('bg-green-50', 'dark:bg-green-900/20', 'border-green-300', 'dark:border-green-700');
        from.classList.remove('bg-red-50', 'dark:bg-red-900/20', 'border-red-300', 'dark:border-red-700');

        // Manage empty state placeholders
        // Remove empty state from target container if it now has real steps
        const toPlaceholder = to.querySelector('.empty-state-item');
        const toRealSteps = [...to.children].filter(child => !child.classList.contains('empty-state-item'));
        if (toPlaceholder && toRealSteps.length > 0) {
          toPlaceholder.remove();
          to.classList.remove('min-h-[120px]', 'flex', 'items-center', 'justify-center');
        }

        // Show empty state in source container if it's now empty
        const fromPlaceholder = from.querySelector('.empty-state-item');
        const fromRealSteps = [...from.children].filter(child => !child.classList.contains('empty-state-item'));
        if (fromRealSteps.length === 0 && !fromPlaceholder) {
          // Create and add empty state placeholder
          const emptyState = document.createElement('li');
          emptyState.className = 'empty-state-item flex flex-col items-center justify-center text-center py-8 text-gray-400 dark:text-gray-500 w-full list-none';
          const category = from.dataset.category || '';
          let emptyMessage = 'No steps configured';
          if (category === 'pre_invite') {
            emptyMessage = 'No pre-invite steps configured';
          } else if (category === 'post_invite') {
            emptyMessage = 'No post-invite steps configured';
          }
          emptyState.innerHTML = `
            <svg class="w-12 h-12 mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
            <p class="text-sm">${emptyMessage}</p>
          `;
          from.appendChild(emptyState);
          from.classList.add('min-h-[120px]', 'flex', 'items-center', 'justify-center');
        } else if (fromPlaceholder && fromRealSteps.length === 0) {
          // Show existing placeholder if container is now empty
          fromPlaceholder.style.display = '';
          from.classList.add('min-h-[120px]', 'flex', 'items-center', 'justify-center');
        }

        if (isCategoryAware) {
          // Category-aware reordering (for Settings → Wizard page)
          const serverType = to.dataset.server;
          const category = to.dataset.category;
          // Filter out empty state placeholder when collecting step IDs
          const ids = [...to.children]
            .filter(li => !li.classList.contains('empty-state-item'))
            .map(li => Number(li.dataset.id));

          fetch(to.dataset.reorderUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              server_type: serverType,
              category: category,
              order: ids
            })
          })
          .then(response => {
            if (!response.ok) {
              throw new Error(`Server returned ${response.status}`);
            }
            return response.json();
          })
          .then(data => {
            if (data.status === 'ok') {
            } else {
              throw new Error(data.message || 'Failed to reorder steps');
            }
          })
          .catch(error => {
            console.error('Failed to reorder steps:', error);
            showToast('Failed to reorder steps. Refreshing page...', 'error');
            // Reload page to revert UI on error
            setTimeout(() => location.reload(), 2000);
          });
        } else if (isBundleList) {
          const bundleId = to.dataset.bundle || from.dataset.bundle;
          const reorderUrl = to.dataset.reorderUrl || from.dataset.reorderUrl;

          if (!bundleId || !reorderUrl) {
            return;
          }

          const relatedLists = [...document.querySelectorAll(`.bundle-steps[data-bundle="${bundleId}"]`)]
            .sort((a, b) => {
              const aIndex = Number(a.dataset.bundleColumn || 0);
              const bIndex = Number(b.dataset.bundleColumn || 0);
              return aIndex - bIndex;
            });

          const orderedItems = [];
          relatedLists.forEach(list => {
            const targetCategory = list.dataset.category || '';
            [...list.children]
              .filter(li => !li.classList.contains('empty-state-item'))
              .forEach(li => {
                const id = Number(li.dataset.id);
                if (!Number.isFinite(id)) {
                  return;
                }

                let category = targetCategory;
                if (!category || category === 'other') {
                  category = li.dataset.category || null;
                }

                if (list === to && item === li && targetCategory && targetCategory !== 'other') {
                  category = targetCategory;
                }

                const normalisedCategory = category || null;
                const originalCategory = li.dataset.originalCategory || null;
                const categoryPayload =
                  !normalisedCategory || (originalCategory && normalisedCategory === originalCategory)
                    ? null
                    : normalisedCategory;

                li.dataset.category = normalisedCategory || '';
                li.dataset.originalCategory = li.dataset.category;

                orderedItems.push({
                  id,
                  category: categoryPayload
                });
              });
          });

          fetch(reorderUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order: orderedItems })
          })
          .catch(error => {
            console.error('Failed to reorder bundle steps:', error);
            showToast('Failed to reorder steps', 'error');
          });
        } else {
          // Legacy reordering for single bundle list instances
          const ids = [...to.children]
            .filter(li => !li.classList.contains('empty-state-item'))
            .map(li => Number(li.dataset.id));
          fetch(to.dataset.reorderUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(ids)
          })
          .catch(error => {
            console.error('Failed to reorder bundle steps:', error);
            showToast('Failed to reorder steps', 'error');
          });
        }
      }
    };

    // For category-aware lists, enable dragging between categories of the same server
    if (isCategoryAware) {
      sortableConfig.group = {
        name: 'wizard-steps-' + container.dataset.server,
        pull: true,
        put: function(to, from, dragEl) {
          // Only allow drops within the same server type
          return to.el.dataset.server === from.el.dataset.server;
        }
      };
    }

    if (isBundleList) {
      sortableConfig.group = {
        name: 'bundle-steps-' + (container.dataset.bundle || ''),
        pull: true,
        put: function(to, from) {
          return to.el.dataset.bundle === from.el.dataset.bundle;
        }
      };
    }

    new Sortable(container, sortableConfig);
    container.dataset.sortableAttached = '1';
  });
}

// Attach Next-button gating that requires an interaction inside step content
function attachInteractionGating(root = document) {
  // Cleanup any previous interaction coordinator
  if (typeof cleanupWizardInteractions === 'function') {
    cleanupWizardInteractions();
  }

  // Handle both mobile and desktop next buttons (updated after button refactoring)
  const mobileNext = root.querySelector('#wizard-next-btn');
  const desktopNext = root.querySelector('#wizard-next-btn-desktop');

  // Get all next buttons that exist
  const nextButtons = [mobileNext, desktopNext].filter(btn => btn !== null);

  if (nextButtons.length === 0) return;

  // Check if any button requires interaction (they should all have same state)
  const requiresInteraction = nextButtons.some(btn => btn.dataset.disabled === '1');
  if (!requiresInteraction) return;

  // Check for new modular interactions config
  const wizardWrapper = root.querySelector('#wizard-wrapper') || root.querySelector('#wizard-content');
  let interactionsConfig = null;

  if (wizardWrapper && wizardWrapper.dataset.interactions) {
    try {
      interactionsConfig = JSON.parse(wizardWrapper.dataset.interactions);
    } catch (e) {
      console.warn('Failed to parse interactions config:', e);
    }
  }

  // Shared enable function that enables ALL next buttons at once
  function enableAllButtons() {
    nextButtons.forEach(next => {
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

      // Remove blockers using stored references
      if (next._clickBlocker) {
        next.removeEventListener('click', next._clickBlocker, true);
        delete next._clickBlocker;
      }
      if (next._keyBlocker) {
        next.removeEventListener('keydown', next._keyBlocker, true);
        delete next._keyBlocker;
      }
    });

    // Remove content listener (legacy fallback)
    const content = root.querySelector('#wizard-wrapper .prose') || root.querySelector('#wizard-content .prose');
    if (content && content._interactionHandler) {
      content.removeEventListener('click', content._interactionHandler, true);
      delete content._interactionHandler;
    }
  }

  // Disable all buttons first
  nextButtons.forEach(next => {
    if (next.dataset.interactionGatingAttached === '1') return;
    next.dataset.interactionGatingAttached = '1';

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

    // 3) Apply disabled affordance & interaction lock
    next.setAttribute('tabindex', '-1');
    next.style.opacity = '0.6';
    next.style.cursor = 'not-allowed';

    // Store button-specific handlers for cleanup
    next._clickBlocker = clickBlocker;
    next._keyBlocker = keyBlocker;
  });

  // Use new modular interaction system if config is present and has enabled interactions
  const hasModularInteractions = interactionsConfig && (
    interactionsConfig.click?.enabled ||
    interactionsConfig.time?.enabled ||
    interactionsConfig.tos?.enabled ||
    interactionsConfig.text_input?.enabled ||
    interactionsConfig.quiz?.enabled
  );

  if (hasModularInteractions && typeof initWizardInteractions === 'function') {
    // Use new modular interaction coordinator
    initWizardInteractions(interactionsConfig, enableAllButtons);
  } else {
    // Legacy fallback: click-based interaction
    // Single interaction handler for the content area
    function handler(ev) {
      const t = ev.target;
      if (!t) return;
      if (t.closest && t.closest('a,button') !== null) enableAllButtons();
    }

    // Listen for any click within the content that bubbles/captures from links/buttons
    const content = root.querySelector('#wizard-wrapper .prose') || root.querySelector('#wizard-content .prose');
    if (content) {
      content.addEventListener('click', handler, true);
      content._interactionHandler = handler; // Store for cleanup
    }
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
