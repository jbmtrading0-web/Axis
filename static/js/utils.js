/**
 * utils.js – shared utility functions for Axis
 */

/**
 * Format a number as BRL currency (R$ 1.234,56)
 */
function formatBRL(value) {
  if (value == null || isNaN(value)) return 'R$ 0,00';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
  }).format(value);
}

/**
 * Format ISO date string (YYYY-MM-DD) to Brazilian format (DD/MM/AAAA)
 */
function formatDate(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.slice(0, 10).split('-');
  return `${d}/${m}/${y}`;
}

/**
 * Escape HTML to prevent XSS when inserting user content into innerHTML
 */
function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Show a temporary toast notification
 * @param {string} msg
 * @param {'success'|'error'|'info'} type
 */
function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

/**
 * Open the global modal with a title and HTML content
 */
function openModal(title, bodyHtml) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = bodyHtml;
  document.getElementById('modal-overlay').classList.add('active');
  document.getElementById('modal').classList.add('active');
}

/**
 * Close the global modal
 */
function closeModal() {
  document.getElementById('modal-overlay').classList.remove('active');
  document.getElementById('modal').classList.remove('active');
  document.getElementById('modal-body').innerHTML = '';
}

/**
 * Toggle sidebar visibility (mobile)
 */
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ─────────────────────────────────────────────
// HTTP helpers
// ─────────────────────────────────────────────

async function _request(method, url, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== null) opts.body = JSON.stringify(body);
  try {
    const res = await fetch(url, opts);
    if (!res.ok) {
      const ct = res.headers.get('Content-Type') || '';
      let errMsg;
      if (ct.includes('application/json')) {
        const errData = await res.json();
        errMsg = errData.erro || errData.message || JSON.stringify(errData);
      } else {
        errMsg = await res.text();
      }
      showToast(`Erro ${res.status}: ${errMsg}`, 'error');
      return null;
    }
    const ct = res.headers.get('Content-Type') || '';
    if (ct.includes('application/json')) return await res.json();
    return true;
  } catch (e) {
    showToast('Erro de conexão: ' + e.message, 'error');
    return null;
  }
}

async function apiGet(url)            { return _request('GET', url); }
async function apiPost(url, body)     { return _request('POST', url, body); }
async function apiPut(url, body)      { return _request('PUT', url, body); }
async function apiDelete(url)         { return _request('DELETE', url); }
