/**
 * app.js – Control Operativo de las Móviles
 * Módulo ES6 compartido por todas las páginas.
 */

export const API_BASE = '/api/v1';

// ─────────────────────────────────────────────────────────────
//  AUTH HELPERS
// ─────────────────────────────────────────────────────────────

export function getToken() {
  return localStorage.getItem('cm_token');
}

export function getUser() {
  try { return JSON.parse(localStorage.getItem('cm_user') || 'null'); }
  catch { return null; }
}

export function isAuthenticated() {
  return !!getToken();
}

export function requireAuth() {
  if (!isAuthenticated()) {
    window.location.href = '/app/login.html';
    throw new Error('No autenticado');
  }
}

export function logout() {
  localStorage.removeItem('cm_token');
  localStorage.removeItem('cm_user');
  window.location.href = '/app/login.html';
}

// ─────────────────────────────────────────────────────────────
//  HTTP CLIENT
// ─────────────────────────────────────────────────────────────

export async function apiRequest(method, endpoint, body = null, isFormData = false) {
  const token = getToken();
  const headers = {};

  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (body && !isFormData) headers['Content-Type'] = 'application/json';

  const opts = { method, headers };
  if (body) opts.body = isFormData ? body : JSON.stringify(body);

  const res = await fetch(`${API_BASE}${endpoint}`, opts);

  if (res.status === 401) {
    logout();
    throw new Error('Sesión expirada. Iniciá sesión nuevamente.');
  }

  let data;
  try { data = await res.json(); } catch { data = {}; }

  if (!res.ok) {
    throw new Error(data.detail || `Error ${res.status}`);
  }
  return data;
}

// ─────────────────────────────────────────────────────────────
//  AUTH ACTIONS
// ─────────────────────────────────────────────────────────────

export async function login(username, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  let data;
  try { data = await res.json(); } catch { data = {}; }
  if (!res.ok) {
    const errorMsg = Array.isArray(data.detail) ? 'Datos incorrectos' : (data.detail || 'Credenciales incorrectas');
    throw new Error(errorMsg);
  }
  return data;
}

// ─────────────────────────────────────────────────────────────
//  API SHORTCUTS
// ─────────────────────────────────────────────────────────────

export const getMobiles      = ()     => apiRequest('GET', '/mobiles');
export const getMobile       = (id)   => apiRequest('GET', `/mobiles/${id}`);
export const createMobile    = (body) => apiRequest('POST', '/mobiles', body);
export const getTechnicians  = ()     => apiRequest('GET', '/technicians');
export const getDashboard    = ()     => apiRequest('GET', '/dashboard');
export const getInspections  = (q='') => apiRequest('GET', `/inspections${q}`);
export const getInspection   = (id)  => apiRequest('GET', `/inspections/${id}`);
export const getOrders       = (q='') => apiRequest('GET', `/orders${q}`);
export const getGuarantees   = ()     => apiRequest('GET', '/guarantees');

// ─────────────────────────────────────────────────────────────
//  UI HELPERS
// ─────────────────────────────────────────────────────────────

let _toastContainer = null;

function getToastContainer() {
  if (!_toastContainer) {
    _toastContainer = document.createElement('div');
    _toastContainer.className = 'toast-container';
    document.body.appendChild(_toastContainer);
  }
  return _toastContainer;
}

export function showToast(message, type = 'success') {
  const container = getToastContainer();
  const toast = document.createElement('div');
  const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

// ─────────────────────────────────────────────────────────────
//  DATE / FORMAT
// ─────────────────────────────────────────────────────────────

export function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('es-PA', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
}

export function formatDateTime(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString('es-PA', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

export function formatTime(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleTimeString('es-PA', {
    hour: '2-digit', minute: '2-digit'
  });
}

export function todayISO() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

// ─────────────────────────────────────────────────────────────
//  SEMÁFORO
// ─────────────────────────────────────────────────────────────

export function getSemaforo(score) {
  const s = Number(score) || 0;
  if (s >= 85) return { cls: 'green',  label: 'ÓPTIMO',   emoji: '🟢' };
  if (s >= 65) return { cls: 'amber',  label: 'REGULAR',  emoji: '🟡' };
  return              { cls: 'red',    label: 'CRÍTICO',  emoji: '🔴' };
}

export function semafBadge(score) {
  const { cls, label } = getSemaforo(score);
  return `<span class="semaforo-badge ${cls}">${label}</span>`;
}

export function semafDot(score) {
  const { cls } = getSemaforo(score);
  return `<span class="semaforo-dot ${cls}"></span>`;
}

// ─────────────────────────────────────────────────────────────
//  SCORE COLOR
// ─────────────────────────────────────────────────────────────

export function scoreColor(s) {
  const n = Number(s) || 0;
  if (n >= 85) return 'var(--teal)';
  if (n >= 65) return 'var(--amber)';
  return 'var(--red)';
}

// ─────────────────────────────────────────────────────────────
//  MODALS
// ─────────────────────────────────────────────────────────────

export function openModal(overlayId) {
  const el = document.getElementById(overlayId);
  if (el) el.classList.add('open');
}

export function closeModal(overlayId) {
  const el = document.getElementById(overlayId);
  if (el) el.classList.remove('open');
}

export function setupModalClose(overlayId) {
  const overlay = document.getElementById(overlayId);
  if (!overlay) return;
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeModal(overlayId);
  });
}

// ─────────────────────────────────────────────────────────────
//  IMAGE COMPRESSION
// ─────────────────────────────────────────────────────────────

export function compressImage(file, maxW = 900, quality = 0.78) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        let { width: w, height: h } = img;
        if (w > maxW) { h = Math.round(h * maxW / w); w = maxW; }
        const canvas = document.createElement('canvas');
        canvas.width = w; canvas.height = h;
        canvas.getContext('2d').drawImage(img, 0, 0, w, h);
        canvas.toBlob(resolve, 'image/jpeg', quality);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
}

// ─────────────────────────────────────────────────────────────
//  SKELETON LOADER
// ─────────────────────────────────────────────────────────────

export function skeletonCards(count = 3) {
  return Array.from({ length: count })
    .map(() => `<div class="skeleton skeleton-card"></div>`)
    .join('');
}

// ─────────────────────────────────────────────────────────────
//  BOTTOM NAV ACTIVE STATE
// ─────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;
  document.querySelectorAll('.bnav-item').forEach(item => {
    const href = item.getAttribute('href') || '';
    if (href && path.includes(href.replace('.html', ''))) {
      item.classList.add('active');
    }
  });
});
