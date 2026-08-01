/**
 * app.js -- Steam Free Games Claimer Frontend
 * by ahmad3a4 · github.com/ahmad3a4/steam-free-claimer
 *
 * Flow: Login → (2FA if needed) → Auto-search → Results → Claim
 */

// ── State ──────────────────────────────────────────────────────────────────
let sessionCreds = {};   // { sessionid, loginSecure } after successful login
let twoFaState   = {};   // { client_id, steamid, request_id, code_type }
let foundGames   = [];

// ── Phase management ───────────────────────────────────────────────────────
function showPhase(id) {
  document.querySelectorAll('.phase').forEach(el => el.classList.remove('active'));
  document.getElementById('phase-' + id).classList.add('active');
}

function setLoadingText(main, sub = '') {
  document.getElementById('loading-text').textContent = main;
  document.getElementById('loading-sub').textContent  = sub;
}

// ── Error helpers ──────────────────────────────────────────────────────────
function showError(elId, msg) {
  const el = document.getElementById(elId);
  if (el) { el.textContent = msg; el.classList.add('visible'); }
}
function clearError(elId) {
  const el = document.getElementById(elId);
  if (el) el.classList.remove('visible');
}

// ── Toggle password visibility ─────────────────────────────────────────────
document.querySelectorAll('.toggle-vis').forEach(btn => {
  btn.addEventListener('click', () => {
    const input = btn.previousElementSibling;
    const show  = input.type === 'password';
    input.type  = show ? 'text' : 'password';
    btn.textContent = show ? '🙈' : '👁';
  });
});

// ── Manual cookie toggle ───────────────────────────────────────────────────
document.getElementById('toggle-manual').addEventListener('click', () => {
  const sec = document.getElementById('manual-section');
  const isHidden = sec.style.display === 'none';
  sec.style.display = isHidden ? 'block' : 'none';
  document.getElementById('toggle-manual').textContent =
    isHidden ? 'Hide manual option' : 'Use session cookies instead';
});

// ── Back to login ──────────────────────────────────────────────────────────
document.getElementById('back-to-login').addEventListener('click', () => {
  clearError('twofa-error');
  showPhase('login');
});

// ══════════════════════════════════════════════════════════════════════════
// 1. LOGIN FORM
// ══════════════════════════════════════════════════════════════════════════
document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  clearError('login-error');

  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;

  if (!username || !password) {
    showError('login-error', 'Please enter your Steam username and password.');
    return;
  }

  showPhase('loading');
  setLoadingText('Signing into Steam…', 'Verifying your credentials securely');

  try {
    const res  = await fetch('/api/login', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ username, password }),
    });
    const data = await res.json();

    if (!res.ok) {
      showPhase('login');
      showError('login-error', data.error || 'Login failed. Try again.');
      return;
    }

    if (data.need_2fa) {
      // Steam Guard required
      twoFaState = {
        client_id:  data.client_id,
        steamid:    data.steamid,
        request_id: data.request_id,
        code_type:  data.code_type,
      };
      document.getElementById('twofa-sub').textContent =
        data.type === 'mobile'
          ? 'Enter the code from your Steam Authenticator app.'
          : 'Check your email for a Steam Guard code.';
      document.getElementById('twofa-code').value = '';
      clearError('twofa-error');
      showPhase('2fa');
    } else {
      // No 2FA — straight to search
      sessionCreds = { sessionid: data.sessionid, loginSecure: data.steamLoginSecure };
      await doSearch();
    }

  } catch {
    showPhase('login');
    showError('login-error', 'Network error — is the Flask server running?');
  }
});

// ══════════════════════════════════════════════════════════════════════════
// 2. MANUAL COOKIE FORM (fallback)
// ══════════════════════════════════════════════════════════════════════════
document.getElementById('cookie-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  clearError('login-error');

  const sessionid  = document.getElementById('sessionid').value.trim();
  const loginSecure = document.getElementById('loginSecure').value.trim();

  if (!sessionid || !loginSecure) {
    showError('login-error', 'Please enter both cookies.');
    return;
  }

  sessionCreds = { sessionid, loginSecure };
  await doSearch();
});

// ══════════════════════════════════════════════════════════════════════════
// 3. STEAM GUARD (2FA) FORM
// ══════════════════════════════════════════════════════════════════════════
document.getElementById('twofa-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  clearError('twofa-error');

  const code = document.getElementById('twofa-code').value.trim().toUpperCase();
  if (!code) {
    showError('twofa-error', 'Please enter the Steam Guard code.');
    return;
  }

  showPhase('loading');
  setLoadingText('Verifying Steam Guard code…', 'This may take a moment');

  try {
    const res  = await fetch('/api/login/verify', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ ...twoFaState, code }),
    });
    const data = await res.json();

    if (!res.ok) {
      showPhase('2fa');
      showError('twofa-error', data.error || 'Invalid code. Try again.');
      return;
    }

    sessionCreds = { sessionid: data.sessionid, loginSecure: data.steamLoginSecure };
    await doSearch();

  } catch {
    showPhase('2fa');
    showError('twofa-error', 'Network error. Try again.');
  }
});

// Auto-uppercase the 2FA input as the user types
document.getElementById('twofa-code').addEventListener('input', function () {
  const pos = this.selectionStart;
  this.value = this.value.toUpperCase();
  this.setSelectionRange(pos, pos);
});

// ══════════════════════════════════════════════════════════════════════════
// 4. SEARCH FOR FREE GAMES
// ══════════════════════════════════════════════════════════════════════════
async function doSearch() {
  showPhase('loading');
  setLoadingText('Searching Steam store…', 'Finding all free game promotions');

  try {
    const res  = await fetch('/api/search', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(sessionCreds),
    });
    const data = await res.json();

    if (!res.ok) {
      showPhase('login');
      showError('login-error', data.error || 'Search failed. Try signing in again.');
      return;
    }

    foundGames = data.games;
    renderGames(foundGames);
    showPhase('results');

  } catch {
    showPhase('login');
    showError('login-error', 'Network error during search. Try again.');
  }
}

// ══════════════════════════════════════════════════════════════════════════
// 5. RENDER GAMES
// ══════════════════════════════════════════════════════════════════════════
function renderGames(games) {
  const list     = document.getElementById('games-list');
  const countEl  = document.getElementById('results-count');
  const claimBtn = document.getElementById('claim-btn');

  const claimable = games.filter(g => g.has_free_packages);
  countEl.innerHTML =
    `Found <strong>${games.length}</strong> free game${games.length !== 1 ? 's' : ''} — ` +
    `<strong>${claimable.length}</strong> claimable`;

  if (games.length === 0) {
    list.innerHTML = `
      <div class="no-games">
        <span class="big-icon">😔</span>
        No free games right now. Check back during Steam sales or special events!
      </div>`;
    claimBtn.style.display = 'none';
    document.getElementById('action-row').style.display = 'flex';
    return;
  }

  list.innerHTML = games.map((game, i) => `
    <div class="game-card" id="game-${game.appid}" style="animation-delay:${i * 0.04}s" role="listitem">
      <div class="game-card-left">
        <div class="game-img-placeholder">🎮</div>
        <div class="game-info">
          <a href="${game.store_url}" target="_blank" rel="noopener"
             class="game-name" title="${escHtml(game.name)}">
            ${escHtml(game.name)}
          </a>
          <div class="game-appid">App ID: ${game.appid}</div>
        </div>
      </div>
      <span class="badge ${game.has_free_packages ? 'badge-free' : 'badge-skip'}">
        ${game.has_free_packages ? '⬦ Free to Claim' : 'No Package'}
      </span>
    </div>
  `).join('');

  claimBtn.style.display = claimable.length === 0 ? 'none' : '';
  claimBtn.textContent   = `Claim All ${claimable.length} Game${claimable.length !== 1 ? 's' : ''} →`;

  document.getElementById('action-row').style.display = 'flex';
  document.getElementById('summary-bar').style.display = 'none';
}

// ══════════════════════════════════════════════════════════════════════════
// 6. CLAIM
// ══════════════════════════════════════════════════════════════════════════
document.getElementById('claim-btn').addEventListener('click', async () => {
  const claimable = foundGames.filter(g => g.has_free_packages);
  if (!claimable.length) return;

  const btn      = document.getElementById('claim-btn');
  btn.disabled   = true;
  btn.textContent = `Claiming ${claimable.length} game${claimable.length !== 1 ? 's' : ''}…`;

  try {
    const res  = await fetch('/api/claim', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ ...sessionCreds, games: claimable }),
    });
    const data = await res.json();

    if (!res.ok) {
      btn.disabled   = false;
      btn.textContent = 'Retry Claim';
      alert(data.error || 'Claim failed.');
      return;
    }

    applyClaimResults(data.results);
    showSummary(data.summary);
    btn.style.display = 'none';

  } catch {
    btn.disabled   = false;
    btn.textContent = 'Retry Claim';
    alert('Network error during claiming. Try again.');
  }
});

function applyClaimResults(results) {
  results.forEach(r => {
    const card  = document.getElementById('game-' + r.appid);
    if (!card) return;
    const badge = card.querySelector('.badge');
    if (!badge) return;

    card.classList.remove('claimed');

    const map = {
      claimed:      ['badge-claimed', '✓ Claimed!'],
      already_owned:['badge-owned',   '★ Already Owned'],
      failed:       ['badge-fail',    '✕ Failed'],
    };
    const [cls, label] = map[r.status] || ['badge-skip', 'Skipped'];
    badge.className  = `badge ${cls}`;
    badge.textContent = label;
    if (r.status === 'claimed') card.classList.add('claimed');
  });
}

function showSummary(s) {
  const bar = document.getElementById('summary-bar');
  bar.innerHTML = `
    <div class="summary-stat claimed-stat">
      <span class="stat-num">${s.claimed}</span>
      <span class="stat-label">Claimed</span>
    </div>
    <div class="summary-stat owned-stat">
      <span class="stat-num">${s.already_owned}</span>
      <span class="stat-label">Already Owned</span>
    </div>
    <div class="summary-stat skip-stat">
      <span class="stat-num">${(s.skipped || 0) + (s.failed || 0)}</span>
      <span class="stat-label">Skipped</span>
    </div>`;
  bar.style.display = 'grid';
}

// ── Reset ──────────────────────────────────────────────────────────────────
document.getElementById('reset-btn').addEventListener('click', () => {
  foundGames   = [];
  sessionCreds = {};
  twoFaState   = {};
  document.getElementById('login-form').reset();
  document.getElementById('twofa-form').reset();
  document.getElementById('manual-section').style.display = 'none';
  document.getElementById('toggle-manual').textContent = 'Use session cookies instead';
  document.getElementById('summary-bar').style.display = 'none';
  clearError('login-error');
  clearError('twofa-error');
  showPhase('login');
});

// ── Utility ────────────────────────────────────────────────────────────────
function escHtml(str) {
  return str
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
