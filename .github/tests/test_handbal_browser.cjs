const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const path = require("node:path");
const root = path.resolve(__dirname, "../../programmas/handbal-live");
async function run() {
 const ids = ["source", "start", "end", "apolloon-first", "status", "matches", "period",
  "settings", "prev", "current", "next", "refresh"];
 const elements = Object.fromEntries(ids.map(id => [id, {
  value: "", disabled: id === "source", checked: true, textContent: "", childElementCount: 0,
  replaceChildren() { this.innerHTML = ""; this.childElementCount = 0; },
  set innerHTML(html) { this.html = html; this.childElementCount = html.includes("<article") ? 1 : 0; },
  get innerHTML() { return this.html || ""; }
 }]));
 const buttons = ["prev", "current", "next", "refresh"].map(id => elements[id]);
 const fields = ["source", "start", "end", "apolloon-first"].map(id => elements[id]);
 const query = "source=https%3A%2F%2Fwww.clubee.com%2Fhandballbelgium%2Ftestv4&from=2026-11-23&to=2026-11-29&apolloon=1";
 let payload = {query, from: "23/11/2026", to: "29/11/2026", options: '<option value="test">Test</option>',
  period: "23/11/2026 - 29/11/2026", html: "<article>Match</article>", status: "One match"};
 let ok = true, requested, timer, address;
 const context = vm.createContext({
  document: {getElementById: id => elements[id], querySelectorAll: selector => selector === "button" ? buttons : fields},
  location: {search: "?view=ticker&from=2026-11-23&to=2026-11-29"},
  history: {replaceState: (_, __, url) => { address = url; }},
  URLSearchParams, AbortSignal, Error,
  clearTimeout() {}, setTimeout(callback) { timer = callback; },
  async fetch(url) { requested = url; return {ok, json: async () => payload}; }
 });
 vm.runInContext(fs.readFileSync(path.join(root, "index.js"), "utf8"), context);
 await new Promise(resolve => setImmediate(resolve));
 assert(!new URL(requested, "http://localhost").searchParams.has("view"), "Index URL cannot select ticker response");
 assert.equal(elements.matches.innerHTML, "<article>Match</article>");
 assert.equal(address, "?" + query);
 assert.equal(elements.source.disabled, false);
 assert.equal(elements.start.disabled, false);
 elements.source.value = "https://www.clubee.com/handballbelgium/testv4";
 payload = {...payload, options: null, error: "Upstream unavailable"}; ok = false;
 await vm.runInContext('refresh("")', context);
 assert.equal(elements.matches.innerHTML, "<article>Match</article>", "Same-filter outage retains last results");
 assert(elements.status.textContent.includes("laatst opgehaalde"));
 payload = {...payload, query: query.replace("2026-11-23", "2026-11-30"), from: "30/11/2026"};
 await vm.runInContext('refresh("next")', context);
 assert.equal(new URL(requested, "http://localhost").searchParams.get("action"), "next");
 assert.equal(elements.matches.innerHTML, "", "Changed-filter outage clears old results");
 assert.equal(elements.start.disabled, false, "Error restores controls");
 assert.equal(typeof timer, "function", "Errors schedule retry");

 const listeners = {};
 const tickerElements = Object.fromEntries(["games", "track", "viewport", "status", "pause"].map(id => [id, {
  textContent: "", innerHTML: "", style: {}, clientWidth: 500,
  getBoundingClientRect: () => ({width: 200}),
  addEventListener(name, callback) { listeners[id + ":" + name] = callback; },
  querySelectorAll: () => [], append() {}, setAttribute() {}
 }]));
 let frame;
 const tickerContext = vm.createContext({
  document: {getElementById: id => tickerElements[id], body: {classList: {toggle() {}}}},
  location: {search: "?speed=99&start=2026-01-01&end=2026-01-07"},
  matchMedia: () => ({matches: false, addEventListener() {}}),
  ResizeObserver: class { observe() {} }, URLSearchParams, AbortSignal, Error,
  requestAnimationFrame(callback) { frame = callback; }, setTimeout() {},
  async fetch(url) { requested = url; return {ok: true, json: async () => ({
   html: "Geen wedstrijden van Apolloon Spurs in deze periode", hasGames: false, warning: "", checkedAt: "12:00:00"
  })}; }
 });
 vm.runInContext(fs.readFileSync(path.join(root, "ticker.js"), "utf8"), tickerContext);
 await new Promise(resolve => setImmediate(resolve));
 assert(requested.includes("view=ticker") && requested.includes("start=2026-01-01"));
 frame(1000); frame(2000);
 assert.equal(tickerElements.track.style.transform, "", "Empty ticker does not scroll");
 listeners["pause:click"]();
 assert.equal(tickerElements.pause.textContent, "Afspelen", "Pause remains available");
 console.log("All browser regression checks passed.");
}
run().catch(error => { console.error(error); process.exitCode = 1; });
