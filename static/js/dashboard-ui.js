/**
 * dashboard-ui.js – Data-Ink micro-visualizations for Axis Dashboard
 *
 * Provides:
 *   drawSparkline(containerId, values, color)  — inline SVG sparkline
 *   renderDelta(containerId, current, previous, inverse)  — Δ% badge
 *   renderProgress(containerId, value, max)  — thin progress fill
 *   showSkeletons(ids) / hideSkeletons(ids)  — skeleton loader helpers
 *
 * No external dependencies. Pure SVG + DOM.
 */

// ─── Sparkline ─────────────────────────────────────────────────────────────

/**
 * Build an inline SVG sparkline string.
 * @param {number[]} values   Array of numeric data points (min 2)
 * @param {string}   color    Stroke/fill colour (CSS colour string)
 * @param {string}   gradId   Unique gradient id for the SVG defs
 * @returns {string} SVG markup
 */
function _buildSparklineSVG(values, color, gradId) {
  var W = 200, H = 44, padX = 4, padY = 6;
  var nums = values.map(function (v) { return +v || 0; });
  var minV = Math.min.apply(null, nums);
  var maxV = Math.max.apply(null, nums);
  var range = maxV - minV || 1;
  var n = nums.length;
  var xStep = (W - padX * 2) / (n - 1);

  var pts = nums.map(function (v, i) {
    var x = +(padX + i * xStep).toFixed(2);
    var y = +(H - padY - ((v - minV) / range) * (H - padY * 2)).toFixed(2);
    return [x, y];
  });

  var linePath = pts.map(function (p, i) {
    return (i === 0 ? 'M' : 'L') + p[0] + ',' + p[1];
  }).join(' ');

  var areaPath = linePath
    + ' L' + pts[n - 1][0] + ',' + H
    + ' L' + pts[0][0] + ',' + H
    + ' Z';

  var last = pts[n - 1];

  return '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none"'
    + ' aria-hidden="true" focusable="false">'
    + '<defs>'
    + '<linearGradient id="' + gradId + '" x1="0" y1="0" x2="0" y2="1">'
    + '<stop offset="0%" stop-color="' + color + '" stop-opacity="0.25"/>'
    + '<stop offset="100%" stop-color="' + color + '" stop-opacity="0"/>'
    + '</linearGradient>'
    + '</defs>'
    + '<path d="' + areaPath + '" fill="url(#' + gradId + ')"/>'
    + '<path d="' + linePath + '" fill="none" stroke="' + color
    + '" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    + '<circle cx="' + last[0] + '" cy="' + last[1] + '" r="3" fill="' + color + '"/>'
    + '</svg>';
}

/**
 * Render a sparkline into a DOM element.
 * @param {string}   containerId  ID of the target element
 * @param {number[]} values       Data series (≥2 points)
 * @param {string}   color        Line colour
 */
function drawSparkline(containerId, values, color) {
  var el = document.getElementById(containerId);
  if (!el) return;
  if (!values || values.length < 2) { el.innerHTML = ''; return; }
  var gradId = 'sg-' + containerId.replace(/[^a-z0-9]/gi, '-').replace(/^-+|-+$/g, '') || 'spark';
  el.innerHTML = _buildSparklineSVG(values, color, gradId);
  el.setAttribute('role', 'img');
  el.setAttribute('aria-label', 'Tendência dos últimos ' + values.length + ' meses');
}

// ─── Delta badge ────────────────────────────────────────────────────────────

/** Minimum absolute percentage change to show a delta badge (0.05 = 0.05%). */
var DELTA_THRESHOLD = 0.05;

/**
 * Render a Δ% badge comparing current vs previous value.
 * @param {string}  containerId  ID of the span/element
 * @param {number}  current      Current period value
 * @param {number}  previous     Previous period value
 * @param {boolean} [inverse]    When true, "up" is bad (red) – use for despesas
 */
function renderDelta(containerId, current, previous, inverse) {
  var el = document.getElementById(containerId);
  if (!el) return;

  if (!previous || previous === 0) {
    el.textContent = '';
    el.className = 'summary-delta';
    return;
  }

  var pct = ((current - previous) / Math.abs(previous)) * 100;
  var abs = Math.abs(pct);

  if (abs < DELTA_THRESHOLD) {
    el.textContent = '→ 0%';
    el.className = 'summary-delta delta-neutral';
    el.setAttribute('aria-label', 'Sem variação em relação ao mês anterior');
    return;
  }

  var up = pct > 0;
  // For inverse metrics (despesas): up = bad
  var isGood = inverse ? !up : up;

  el.textContent = (up ? '↑ ' : '↓ ') + abs.toFixed(1) + '%';
  el.className = 'summary-delta ' + (isGood ? 'delta-up' : 'delta-down');
  el.setAttribute('aria-label',
    (up ? 'Aumento' : 'Queda') + ' de ' + abs.toFixed(1) + '% em relação ao mês anterior');
}

// ─── Progress bar ───────────────────────────────────────────────────────────

/**
 * Set the width of a progress fill bar as percentage of max.
 * @param {string} containerId  ID of the fill element (.summary-progress-fill)
 * @param {number} value        Realized value
 * @param {number} max          Target / forecast value
 */
function renderProgress(containerId, value, max) {
  var el = document.getElementById(containerId);
  if (!el) return;
  var pct = max > 0 ? Math.min((Math.abs(value) / Math.abs(max)) * 100, 100) : 0;
  el.style.width = pct.toFixed(1) + '%';
}

// ─── Skeleton helpers ───────────────────────────────────────────────────────

/**
 * Show skeleton loading state on the given card IDs.
 * @param {string[]} ids  Array of card element IDs
 */
function showSkeletons(ids) {
  ids.forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.classList.remove('sk-done');
  });
}

/**
 * Hide skeleton loading state (reveal real content).
 * @param {string[]} ids  Array of card element IDs
 */
function hideSkeletons(ids) {
  ids.forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.classList.add('sk-done');
  });
}
