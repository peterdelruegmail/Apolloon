"use strict";
const params = new URLSearchParams(location.search);
const gamesElement = document.getElementById('games');
const track = document.getElementById('track');
const viewport = document.getElementById('viewport');
const statusElement = document.getElementById('status');
const pauseButton = document.getElementById('pause');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
let paused = reducedMotion.matches;
let hovering = false;
let offset = 0;
let previousFrame = 0;
let signature = '';
let latest = null;
let lastSuccess = '';
const speed = Math.min(300, Math.max(10, Number(params.get('speed')) || 80));
function setPaused(value) {
 paused = value;
 document.body.classList.toggle('paused', paused);
 pauseButton.textContent = paused ? 'Afspelen' : 'Pauzeren';
 pauseButton.setAttribute('aria-pressed', String(paused));
}
pauseButton.addEventListener('click', () => setPaused(!paused));
reducedMotion.addEventListener('change', event => setPaused(event.matches));
viewport.addEventListener('mouseenter', () => { hovering = true; });
viewport.addEventListener('mouseleave', () => { hovering = false; });
viewport.addEventListener('focus', () => setPaused(true));
setPaused(paused);
function copyGames() {
 track.querySelectorAll('.copy').forEach(node => node.remove());
 if (!latest?.length) return;
 const width = gamesElement.getBoundingClientRect().width;
 if (!width) return;
 const count = Math.ceil(viewport.clientWidth / width) + 1;
 for (let i = 0; i < count; i++) {
  const copy = gamesElement.cloneNode(true);
  copy.removeAttribute('id'); copy.classList.add('copy'); copy.setAttribute('aria-hidden', 'true');
  track.append(copy);
 }
}
new ResizeObserver(copyGames).observe(viewport);
function render(games) {
 const nextSignature = JSON.stringify(games);
 if (nextSignature === signature) return;
 signature = nextSignature; latest = games;
 gamesElement.replaceChildren(); offset = 0; track.style.transform = '';
 if (!games.length) gamesElement.textContent = 'Geen wedstrijden van Apolloon Spurs in deze periode';
 for (const game of games) {
  const item = document.createElement('span'); item.className = 'match';
  const date = document.createElement('time'); date.dateTime = game.date;
  date.textContent = game.date.slice(8, 10) + '/' + game.date.slice(5, 7) + ' ' + (game.time || '');
  const home = document.createElement('span'); home.textContent = game.home;
  const score = document.createElement('strong'); score.className = 'score';
  score.textContent = game.cancelled ? 'Afgelast' : (game.score || '-');
  if (game.notUpdated) score.textContent += ' (niet bijgewerkt)';
  const away = document.createElement('span'); away.textContent = game.away;
  item.append(date, home, score, away); gamesElement.append(item);
 }
 copyGames();
}
function animate(timestamp) {
 const elapsed = previousFrame ? Math.min(timestamp - previousFrame, 100) / 1000 : 0;
 previousFrame = timestamp;
 const width = gamesElement.getBoundingClientRect().width;
 if (!paused && !hovering && latest?.length && width > 0) {
  offset = (offset + speed * elapsed) % width;
  track.style.transform = `translateX(${-offset}px)`;
 }
 requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
async function refresh() {
 const query = new URLSearchParams();
 for (const key of ['start', 'end']) if (params.has(key)) query.set(key, params.get(key));
 try {
  const response = await fetch('club-ticker.php?' + query, {cache: 'no-store', signal: AbortSignal.timeout(145000)});
  const data = await response.json();
  if (!response.ok) throw Error(data.error || 'Wedstrijden ophalen is mislukt.');
  if (!Array.isArray(data.games)) throw Error('Ongeldige wedstrijdgegevens.');
  render(data.games);
  lastSuccess = new Date(data.checkedAt).toLocaleTimeString('nl-BE', {timeZone: 'Europe/Brussels'});
  statusElement.textContent = data.warning || '';
  statusElement.hidden = !data.warning;
 } catch (error) {
  statusElement.hidden = false;
  statusElement.textContent = (error.name === 'TimeoutError' ? 'Clubee reageert niet op tijd.' : error.message)
   + (lastSuccess ? ' Laatste geslaagde controle: ' + lastSuccess + '.' : '') + ' Automatisch opnieuw proberen.';
 } finally { setTimeout(refresh, 30000); }
}
refresh();
