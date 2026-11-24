"use strict";
const $ = id => document.getElementById(id);
let busy = false, timer, activeQuery = "", checkedQuery = "";
async function refresh(action = "") {
 if (busy) return;
 busy = true; clearTimeout(timer);
 const sourceUnavailable = $("source").disabled;
 for (const field of document.querySelectorAll("input, select")) field.disabled = true;
 for (const button of document.querySelectorAll("button")) button.disabled = true;
 $("status").textContent = "Nieuwe stand ophalen.";
 const query = action === "init" ? new URLSearchParams(location.search) : new URLSearchParams({
  source: $("source").value, from: $("start").value, to: $("end").value,
  apolloon: $("apolloon-first").checked ? "1" : "0"
 });
 query.delete("view");
 query.set("action", action);
 try {
  const response = await fetch("view.php?" + query, {cache: "no-store", signal: AbortSignal.timeout(145000)});
  const data = await response.json();
  if (data.query) {
   activeQuery = data.query;
   if (data.options !== null) $("source").innerHTML = data.options;
   $("source").disabled = false;
   $("start").value = data.from; $("end").value = data.to;
   $("apolloon-first").checked = new URLSearchParams(data.query).get("apolloon") !== "0";
   $("period").textContent = data.period;
   history.replaceState(null, "", "?" + data.query);
   if (checkedQuery !== activeQuery) $("matches").replaceChildren();
  }
  if (!response.ok || data.error) throw Error(data.error || "Clubee kon niet worden opgehaald.");
  $("matches").innerHTML = data.html;
  checkedQuery = activeQuery;
  $("status").textContent = data.status;
  return {matches: data.count, status: data.status};
 } catch (error) {
  $("status").textContent = (error.name === "TimeoutError" ? "Clubee reageert niet op tijd." : error.message)
   + ($("matches").childElementCount ? " De laatst opgehaalde wedstrijden blijven staan." : "")
   + " Automatisch opnieuw proberen.";
 } finally {
  busy = false;
  for (const field of document.querySelectorAll("input, select")) field.disabled = false;
  $("source").disabled = sourceUnavailable && !activeQuery;
  for (const button of document.querySelectorAll("button")) button.disabled = false;
  timer = setTimeout(() => refresh($("source").disabled ? "init" : ""), 30000);
 }
}
$("settings").onsubmit = event => { event.preventDefault(); refresh(); };
for (const action of ["prev", "current", "next"]) $(action).onclick = () => refresh(action);
$("apolloon-first").onchange = () => refresh();
$("refresh").onclick = () => refresh($("source").disabled ? "init" : "");
refresh("init");

if (document.modelContext?.registerTool) {
 try {
  document.modelContext.registerTool({
   name: "configure_match_view", description: "Stel de Clubee-competitie en het datumbereik in en laad de wedstrijden.",
   inputSchema: {type: "object", properties: {source: {type: "string"}, from: {type: "string"}, to: {type: "string"}},
    required: ["source", "from", "to"], additionalProperties: false},
   annotations: {readOnlyHint: false, untrustedContentHint: true},
   async execute(input) {
    if (busy || !input || ["source", "from", "to"].some(key => typeof input[key] !== "string")) throw Error("Ongeldige invoer of ophalen bezig.");
    $("source").value = input.source; $("start").value = input.from; $("end").value = input.to;
    const result = await refresh();
    if (!result) throw Error($("status").textContent);
    return result;
   }
  });
 } catch (_) {}
}
