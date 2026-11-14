const state = { matches: [], selected: null, settings: { ui_refresh_seconds: 20, theme: 'dark', show_paused: true, highlight_enabled: true, highlight_goal_difference: 3, highlight_remaining_seconds: 90 }, view: 'table' };
const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
const remaining = (match) => {
  if (match.remaining_seconds != null) { const n = Math.max(0, Number(match.remaining_seconds)); return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, '0')}`; }
  return 'szacunek';
};
const format = (match) => match.format_minutes ? `2 × ${Number(match.format_minutes) / 2} min` : 'brak';
const score = (match) => match.score_label || `${match.home_score ?? '–'}:${match.away_score ?? '–'}`;
const matchName = (match) => `${match.home || ''} — ${match.away || ''}`;
function highlightInfo(match) {
  const settings = state.settings;
  if (!settings.highlight_enabled || match.remaining_seconds == null || Number(match.remaining_seconds) < 0 || Number(match.remaining_seconds) > Number(settings.highlight_remaining_seconds)) return null;
  const home = Number(match.home_score), away = Number(match.away_score);
  if (!Number.isInteger(home) || !Number.isInteger(away) || home === away) return null;
  const difference = Math.abs(home - away);
  if (difference < Number(settings.highlight_goal_difference)) return null;
  return {side: home > away ? 'home' : 'away', difference, seconds: Number(match.remaining_seconds)};
}
function teamNamesHtml(match) {
  const info = highlightInfo(match);
  const homeClass = info?.side === 'home' ? 'team-name team-leading-highlight' : 'team-name';
  const awayClass = info?.side === 'away' ? 'team-name team-leading-highlight' : 'team-name';
  return `<span class="${homeClass}">${esc(match.home || '')}</span><span class="team-separator"> — </span><span class="${awayClass}">${esc(match.away || '')}</span>${info ? `<span class="lead-alert">PRZEWAGA ${info.difference}+ · KONIEC ≤ ${Math.floor(info.seconds / 60)}:${String(info.seconds % 60).padStart(2, '0')}</span>` : ''}`;
}
function filteredMatches() {
  const query = $('searchInput').value.trim().toLowerCase(); const half = $('halfFilter').value; const status = $('statusFilter').value; const sort = $('sortSelect').value;
  const list = state.matches.filter((m) => {
    const haystack = `${m.home} ${m.away} ${m.competition}`.toLowerCase();
    return (!query || haystack.includes(query)) && (half === 'all' || String(m.half) === half) && (status === 'all' || m.status === status) && m.is_live !== false;
  });
  list.sort((a, b) => {
    const ar = a.remaining_seconds == null ? Number.POSITIVE_INFINITY : Number(a.remaining_seconds);
    const br = b.remaining_seconds == null ? Number.POSITIVE_INFINITY : Number(b.remaining_seconds);
    if (ar !== br) return ar - br;
    return matchName(a).localeCompare(matchName(b), 'pl') || String(a.key).localeCompare(String(b.key));
  });
  return list;
}
function statusHtml(match) { const paused = match.status !== 'aktywny'; return `<span class="status-dot ${paused ? 'status-paused' : ''}">${esc(match.status || 'brak')}</span>`; }
function render() {
  const list = filteredMatches(); $('resultCount').textContent = `${list.length} wyników`; $('totalMatches').textContent = state.matches.length; $('secondHalf').textContent = state.matches.filter((m) => Number(m.half) === 2).length;
  const next = [...state.matches].sort((a,b) => (a.remaining_seconds ?? 999999) - (b.remaining_seconds ?? 999999))[0]; $('nextMatch').textContent = next ? remaining(next) : '—'; $('nextMatchNote').textContent = next ? matchName(next) : 'brak danych';
  const body = $('matchesBody'); body.innerHTML = list.map((m) => `<tr data-key="${esc(m.key)}" class="${state.selected?.key === m.key ? 'selected' : ''}"><td>${remaining(m)}</td><td class="team-cell">${teamNamesHtml(m)}<small>${esc(m.competition)}</small></td><td class="score">${esc(score(m))}</td><td>${esc(m.half_label || (m.half ? `${m.half}. połowa` : 'brak'))}<br><span class="muted">${esc(m.clock_label || 'brak')}</span></td><td>${esc(m.competition || 'e-Piłka live')}</td><td>${statusHtml(m)}</td></tr>`).join('');
  body.querySelectorAll('tr').forEach((row) => row.addEventListener('click', () => selectMatch(row.dataset.key)));
  $('compactView').innerHTML = list.map((m) => `<article class="match-card" data-key="${esc(m.key)}"><div class="card-top"><span>${esc(m.competition)}</span><span>${remaining(m)}</span></div><h3 class="card-teams">${teamNamesHtml(m)}</h3><span class="card-score">${esc(score(m))}</span><p class="muted">${esc(m.half_label || 'brak')} · ${esc(m.clock_label || 'brak')}</p>${statusHtml(m)}</article>`).join('');
  $('compactView').querySelectorAll('.match-card').forEach((card) => card.addEventListener('click', () => selectMatch(card.dataset.key)));
  $('emptyState').classList.toggle('hidden', list.length !== 0); $('tableView').classList.toggle('hidden', state.view !== 'table'); $('compactView').classList.toggle('hidden', state.view !== 'compact');
  if (state.selected) renderDetail(state.selected);
}
async function selectMatch(key) { state.selected = state.matches.find((m) => m.key === key) || null; render(); if (!state.selected) return; try { const response = await fetch(`/api/history?match_key=${encodeURIComponent(key)}`); const data = await response.json(); renderHistory(data.history || []); } catch (_) { renderHistory([]); } }
function renderDetail(match) {
  $('detailEmpty').classList.add('hidden'); $('detailContent').classList.remove('hidden'); $('detailLive').classList.toggle('hidden', match.status !== 'aktywny'); $('detailCompetition').textContent = match.competition || 'E-PIŁKA LIVE'; $('detailTeams').innerHTML = teamNamesHtml(match); $('detailScore').textContent = score(match); $('detailHalf').textContent = match.half_label || (match.half ? `${match.half}. połowa` : 'brak'); $('detailClock').textContent = match.clock_label || 'brak'; $('detailFormat').textContent = format(match); $('detailRemaining').textContent = remaining(match); $('detailAnalysis').textContent = match.analysis || `Mecz ${match.status || 'live'}, ${match.half_label || 'faza nieznana'}, czas ${match.clock_label || 'brak'}. Dane pochodzą z ostatniej migawki strony.`;
}
function renderHistory(history) { $('historyList').innerHTML = history.length ? history.slice(0, 8).map((row) => `<div class="history-row"><span>${esc(new Date(row.observed_at).toLocaleTimeString())}</span><strong>${esc(row.score || row.score_label || 'brak')} · ${esc(row.clock_label || '')}</strong></div>`).join('') : '<p class="muted">Brak wcześniejszych odczytów.</p>'; }
async function loadLive() { try { const response = await fetch('/api/live', {cache: 'no-store'}); if (!response.ok) throw new Error('HTTP'); const data = await response.json(); state.matches = (data.matches || []).map((m) => ({...m, score_label: score(m), half_label: m.half_label || (m.half ? `${m.half}. połowa` : 'brak')})); $('connectionBadge').textContent = data.source_online ? 'Źródło aktualne' : 'Brak aktualnych danych'; $('connectionBadge').className = data.source_online ? 'badge badge-ok' : 'badge badge-warn'; $('sourceAge').textContent = data.source_age_seconds != null ? `${data.source_age_seconds}s` : '—'; $('sourceNote').textContent = data.source_online ? 'ostatni sygnał Chrome' : (data.source_status === 'stale' ? 'sygnał jest nieaktualny' : 'oczekiwanie na Chrome'); $('lastUpdate').textContent = `Ostatni odczyt panelu: ${new Date().toLocaleTimeString()}`; render(); } catch (_) { $('connectionBadge').textContent = 'Brak połączenia'; $('connectionBadge').className = 'badge badge-warn'; $('sourceNote').textContent = 'uruchom serwer Python'; } }
async function loadSettings() { try { const response = await fetch('/api/settings'); if (response.ok) state.settings = {...state.settings, ...(await response.json())}; } catch (_) {} $('uiRefresh').value = '20'; $('themeSelect').value = state.settings.theme; $('highlightEnabled').checked = Boolean(state.settings.highlight_enabled); $('highlightGoalDifference').value = String(state.settings.highlight_goal_difference ?? 3); $('highlightRemainingSeconds').value = String(state.settings.highlight_remaining_seconds ?? 90); document.body.classList.toggle('light', state.settings.theme === 'light'); }
async function saveSettings(event) { event.preventDefault(); const settings = {ui_refresh_seconds: 20, theme: $('themeSelect').value, show_paused: true, highlight_enabled: $('highlightEnabled').checked, highlight_goal_difference: Math.max(1, Math.min(10, Number($('highlightGoalDifference').value) || 3)), highlight_remaining_seconds: Math.max(15, Math.min(600, Number($('highlightRemainingSeconds').value) || 90))}; try { const response = await fetch('/api/settings', {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(settings)}); if (!response.ok) throw new Error('settings'); state.settings = {...state.settings, ...settings}; document.body.classList.toggle('light', settings.theme === 'light'); $('settingsDialog').close(); render(); startPolling(); } catch (_) { alert('Nie udało się zapisać ustawień. Sprawdź, czy serwer działa.'); } }
let pollTimer; function startPolling() { clearInterval(pollTimer); pollTimer = setInterval(loadLive, 20_000); }
$('refreshBtn').addEventListener('click', loadLive); ['searchInput','halfFilter','statusFilter','sortSelect'].forEach((id) => $(id).addEventListener('input', render)); $('clearFilters').addEventListener('click', () => { $('searchInput').value = ''; $('halfFilter').value = 'all'; $('statusFilter').value = 'all'; render(); }); document.querySelectorAll('.view-btn').forEach((button) => button.addEventListener('click', () => { state.view = button.dataset.view; document.querySelectorAll('.view-btn').forEach((b) => b.classList.toggle('active', b === button)); render(); })); $('settingsBtn').addEventListener('click', () => $('settingsDialog').showModal()); $('settingsForm').addEventListener('submit', saveSettings); loadSettings().then(() => { loadLive(); startPolling(); });
