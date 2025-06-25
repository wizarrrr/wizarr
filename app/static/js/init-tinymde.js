function attachTinyMDE() {
  const modal = document.getElementById('step-modal') || document;
  const textarea = modal.querySelector('textarea[name="markdown"]');
  if (!textarea || textarea.dataset.tinymdeAttached) return;
  textarea.dataset.tinymdeAttached = '1';
  if (typeof TinyMDE === 'undefined') {
    console.warn('TinyMDE not loaded');
    return;
  }
  new TinyMDE.Editor({ textarea: textarea });
  // Style the generated editor to match input fields
  const edRoot = textarea.nextElementSibling; // TinyMDE inserts after textarea
  if (edRoot) {
    edRoot.classList.add(
      'bg-gray-50',
      'border',
      'border-gray-300',
      'rounded-lg',
      'p-2.5',
      'dark:bg-gray-700',
      'dark:border-gray-600',
      'dark:text-white'
    );
  }
}

document.addEventListener('htmx:afterOnLoad', attachTinyMDE);
document.addEventListener('DOMContentLoaded', attachTinyMDE); 