/**
 * app.js – global JS initialisation for Axis
 * Page-specific logic lives in each template's {% block scripts %}.
 * Modal ESC handling is managed by ui/modal.js.
 */

// Highlight active nav link (server-side Jinja handles this; kept for fallback)
document.querySelectorAll('.nav-item').forEach(link => {
  if (link.href === location.href) link.classList.add('active');
});
