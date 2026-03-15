/* ─── Axis Modal System – Fluent Enterprise ─── */
/* Accessible modal: focus trap, ESC to close, backdrop click configurable */
(function (global) {
  'use strict';

  var _closeOnBackdrop = true;
  var _lastFocus = null;

  var FOCUSABLE =
    'a[href], area[href], input:not([disabled]), select:not([disabled]), ' +
    'textarea:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function getFocusableElements(container) {
    return Array.prototype.slice.call(container.querySelectorAll(FOCUSABLE)).filter(function (el) {
      return !el.closest('[hidden]') && el.offsetParent !== null;
    });
  }

  function trapFocus(e) {
    var modal = document.getElementById('modal');
    if (!modal || !modal.classList.contains('active')) return;

    var focusable = getFocusableElements(modal);
    if (!focusable.length) { e.preventDefault(); return; }

    var first = focusable[0];
    var last  = focusable[focusable.length - 1];

    if (e.shiftKey) {
      if (document.activeElement === first) { last.focus(); e.preventDefault(); }
    } else {
      if (document.activeElement === last)  { first.focus(); e.preventDefault(); }
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Escape' || e.keyCode === 27) {
      closeModal();
    }
    if (e.key === 'Tab' || e.keyCode === 9) {
      trapFocus(e);
    }
  }

  /**
   * Open the global modal.
   * @param {string} title        - Modal heading text
   * @param {string} bodyHtml     - Inner HTML for the body
   * @param {object} [options]    - { closeOnBackdrop: boolean }
   */
  function openModal(title, bodyHtml, options) {
    options = options || {};
    _closeOnBackdrop = (options.closeOnBackdrop !== false); /* default true */

    var overlay = document.getElementById('modal-overlay');
    var modal   = document.getElementById('modal');
    var titleEl = document.getElementById('modal-title');
    var bodyEl  = document.getElementById('modal-body');

    if (!overlay || !modal) return;

    _lastFocus = document.activeElement;

    if (titleEl) titleEl.textContent = title;
    if (bodyEl)  bodyEl.innerHTML    = bodyHtml;

    overlay.classList.add('active');
    modal.classList.add('active');
    modal.removeAttribute('aria-hidden');

    document.addEventListener('keydown', onKeyDown);
    document.body.style.overflow = 'hidden';

    /* Move focus to first focusable element or the modal itself */
    requestAnimationFrame(function () {
      var focusable = getFocusableElements(modal);
      if (focusable.length) {
        focusable[0].focus();
      } else {
        modal.setAttribute('tabindex', '-1');
        modal.focus();
      }
    });
  }

  function closeModal() {
    var overlay = document.getElementById('modal-overlay');
    var modal   = document.getElementById('modal');
    var bodyEl  = document.getElementById('modal-body');

    if (!overlay || !modal) return;

    overlay.classList.remove('active');
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');

    document.removeEventListener('keydown', onKeyDown);
    document.body.style.overflow = '';

    if (bodyEl) bodyEl.innerHTML = '';

    if (_lastFocus && typeof _lastFocus.focus === 'function') {
      _lastFocus.focus();
      _lastFocus = null;
    }
  }

  /* Backdrop click handler – attached in base.html via onclick, respects flag */
  function handleBackdropClick() {
    if (_closeOnBackdrop) closeModal();
  }

  /* Expose globally */
  global.openModal  = openModal;
  global.closeModal = closeModal;
  global.handleBackdropClick = handleBackdropClick;
}(window));
