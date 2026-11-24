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
let latest = false;
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
 if (!latest) return;
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
function render(html, hasGames) {
 if (html === signature) return;
 signature = html; latest = hasGames;
 gamesElement.innerHTML = html; offset = 0; track.style.transform = '';
 copyGames();
}
function animate(timestamp) {
 const elapsed = previousFrame ? Math.min(timestamp - previousFrame, 100) / 1000 : 0;
 previousFrame = timestamp;
 const width = gamesElement.getBoundingClientRect().width;
 if (!paused && !hovering && latest && width > 0) {
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
  const response = await fetch('view.php?view=ticker&' + query, {cache: 'no-store', signal: AbortSignal.timeout(145000)});
  const data = await response.json();
  if (!response.ok) throw Error(data.error || 'Wedstrijden ophalen is mislukt.');
  if (typeof data.html !== 'string') throw Error('Ongeldige wedstrijdgegevens.');
  render(data.html, data.hasGames);
  lastSuccess = data.checkedAt;
  statusElement.textContent = data.warning || '';
  statusElement.hidden = !data.warning;
 } catch (error) {
  statusElement.hidden = false;
  statusElement.textContent = (error.name === 'TimeoutError' ? 'Clubee reageert niet op tijd.' : error.message)
   + (lastSuccess ? ' Laatste geslaagde controle: ' + lastSuccess + '.' : '') + ' Automatisch opnieuw proberen.';
 } finally { setTimeout(refresh, 30000); }
}
refresh();
