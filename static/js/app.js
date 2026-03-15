/**
 * app.js – global JS initialisation for Axis
 * Page-specific logic lives in each template's {% block scripts %}.
 */

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

// Highlight active nav link (already done server-side via Jinja but kept for SPA-style fallback)
document.querySelectorAll('.nav-item').forEach(link => {
  if (link.href === location.href) link.classList.add('active');
});
