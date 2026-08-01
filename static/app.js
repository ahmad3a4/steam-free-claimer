/**
 * app.js — Steam Free Games Claimer Frontend
 * by ahmad3a4 · github.com/ahmad3a4/steam-free-claimer
 */

// ── State ──────────────────────────────────────────────────────────────────
let foundGames   = [];
let sessionCreds = {};

// ── Phase management ───────────────────────────────────────────────────────
function showPhase(id) {
  document.querySelectorAll('.phase').forEach(el => el.classList.remove('active'));
  document.getElementById('phase-' + id).classList.add('active');
}

// ── Error helper ───────────────────────────────────────────────────────────
function showError(msg) {
  const el = document.getElementById('error-msg');
  el.textContent = msg;
  el.classList.add('visible');
}
function clearError() {
  document.getElementById('error-msg').classList.remove('visible');
}

// ── Toggle password visibility ─────────────────────────────────────────────
document.querySelectorAll('.toggle-vis').forEach(btn => {
  btn.addEventListener('click', () => {
    const input = btn.previousElementSibling;
    const isPass = input.type === 'password';
    input.type = isPass ? 'text' : 'password';
    btn.textContent = isPass ? '🙈' : '👁';
  });
});

// ── Search form ────────────────────────────────────────────────────────────
document.getElementById('search-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  clearError();

  const sessionid  = document.getElementById('sessionid').value.trim();
  const loginSecure = document.getElementById('loginSecure').value.trim();

  if (!sessionid || !loginSecure) {
    showError('Please enter both sessionid and steamLoginSecure cookies.');
    return;
  }

  sessionCreds = { sessionid, loginSecure };
  showPhase('loading');
  setLoadingText('Verifying Steam session…', 'Checking your cookies are valid');

  try {
    const res = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionid, loginSecure })
    });

    const data = await res.json();

    if (!res.ok) {
      showPhase('input');
      showError(data.error || 'Something went wrong. Try again.');
      return;
    }

    foundGames = data.games;
    renderGames(foundGames);
    showPhase('results');

  } catch (err) {
    showPhase('input');
    showError('Network error — is the server running?');
  }
});

// ── Loading text helper ────────────────────────────────────────────────────
function setLoadingText(main, sub) {
  document.getElementById('loading-text').textContent = main;
  document.getElementById('loading-sub').textContent  = sub || '';
}

// ── Render found games ─────────────────────────────────────────────────────
function renderGames(games) {
  const list = document.getElementById('games-list');
  const countEl = document.getElementById('results-count');
  const claimBtn = document.getElementById('claim-btn');

  const claimable = games.filter(g => g.has_free_packages);
  countEl.innerHTML = `Found <strong>${games.length}</strong> free game${games.length !== 1 ? 's' : ''} — <strong>${claimable.length}</strong> claimable`;

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
    <div class="game-card" id="game-${game.appid}" style="animation-delay:${i * 0.04}s">
      <div class="game-card-left">
        <div class="game-img-placeholder">🎮</div>
        <div class="game-info">
          <a href="${game.store_url}" target="_blank" class="game-name" title="${escHtml(game.name)}">
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

  // Hide claim button if nothing to claim
  if (claimable.length === 0) {
    claimBtn.style.display = 'none';
  } else {
    claimBtn.style.display = '';
    claimBtn.textContent = `Claim All ${claimable.length} Game${claimable.length !== 1 ? 's' : ''} →`;
  }

  document.getElementById('action-row').style.display = 'flex';
  document.getElementById('summary-bar').style.display = 'none';
}

// ── Claim button ───────────────────────────────────────────────────────────
document.getElementById('claim-btn').addEventListener('click', async () => {
  const claimable = foundGames.filter(g => g.has_free_packages);
  if (!claimable.length) return;

  const btn = document.getElementById('claim-btn');
  btn.disabled = true;
  btn.textContent = 'Claiming… please wait';

  try {
    const res = await fetch('/api/claim', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sessionid:   sessionCreds.sessionid,
        loginSecure: sessionCreds.loginSecure,
        games: claimable
      })
    });

    const data = await res.json();

    if (!res.ok) {
      btn.disabled = false;
      btn.textContent = 'Retry Claim';
      alert(data.error || 'Claim failed.');
      return;
    }

    applyClaimResults(data.results);
    showSummary(data.summary);

    btn.style.display = 'none';

  } catch (err) {
    btn.disabled = false;
    btn.textContent = 'Retry Claim';
    alert('Network error during claiming. Try again.');
  }
});

// ── Apply result badges to game cards ─────────────────────────────────────
function applyClaimResults(results) {
  results.forEach(r => {
    const card = document.getElementById('game-' + r.appid);
    if (!card) return;

    const badge = card.querySelector('.badge');
    if (!badge) return;

    card.classList.remove('claimed');

    switch (r.status) {
      case 'claimed':
        badge.className = 'badge badge-claimed';
        badge.textContent = '✓ Claimed!';
        card.classList.add('claimed');
        break;
      case 'already_owned':
        badge.className = 'badge badge-owned';
        badge.textContent = '★ Already Owned';
        break;
      case 'failed':
        badge.className = 'badge badge-fail';
        badge.textContent = '✕ Failed';
        break;
      default:
        badge.className = 'badge badge-skip';
        badge.textContent = 'Skipped';
    }
  });
}

// ── Summary bar ────────────────────────────────────────────────────────────
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

// ── Reset button ───────────────────────────────────────────────────────────
document.getElementById('reset-btn').addEventListener('click', () => {
  foundGames = [];
  sessionCreds = {};
  document.getElementById('search-form').reset();
  document.getElementById('summary-bar').style.display = 'none';
  clearError();
  showPhase('input');
});

// ── Utility ────────────────────────────────────────────────────────────────
function escHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
