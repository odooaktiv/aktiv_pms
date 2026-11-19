/*
 * Aktiv for Outlook - taskpane
 *
 * Data path is: customer's Outlook <-> customer's Odoo. We are never in the
 * middle. Our origin only serves these static files plus /api/license.
 *
 * Auth: a direct username/password (or API key) form posts straight to
 * /aktiv/auth/login (see pluging/aktiv_outlook_plugin/controllers/auth.py). That
 * route authenticates against the given database and, on success, mints the
 * same odoo.plugin.outlook scoped API key mail_plugin's own OAuth dialog flow
 * would have produced - so the create routes validate it with mail_plugin's own
 * _auth_method_outlook (they call it from inside the handler rather than via
 * auth='outlook'; see aktiv_outlook_plugin/controllers/hooks.py for why). We keep
 * only the API key, never the password, in roamingSettings.
 */

const CFG = window.AKTIV_CONFIG || {};
const ADDIN_ORIGIN = CFG.ADDIN_ORIGIN || location.origin;

let settings;

Office.onReady((info) => {
  if (info.host !== Office.HostType.Outlook) return;
  settings = Office.context.roamingSettings;
  document.getElementById("connect-form").addEventListener("submit", onConnectSubmit);
  boot();
});

/* ------------------------------------------------------------------ storage */
/* roamingSettings is per-mailbox and follows the user across their Outlook
   clients. ~32KB limit. Odoo SA stores the API key here too - but note this
   means a permanent Odoo credential lives in mailbox settings. Worth saying
   out loud in your privacy policy; AppSource reviewers do read it. */

const get = (k) => settings.get(k);
const set = (k, v) => settings.set(k, v);

function saveSettings() {
  return new Promise((resolve, reject) => {
    settings.saveAsync((r) =>
      r.status === Office.AsyncResultStatus.Succeeded ? resolve() : reject(r.error)
    );
  });
}

/* ---------------------------------------------------------------- odoo rpc */

function normalizeOdooUrl(raw) {
  let s = String(raw || "").trim().replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(s)) s = "https://" + s;
  const u = new URL(s);
  if (u.protocol !== "https:") throw new Error("Odoo URL must use https://");
  return u.origin;
}

/*
 * fetch() itself rejects (a plain TypeError, no HTTP status attached) when the
 * browser never got a response at all - wrong URL, DNS/connection failure, or
 * a CORS preflight that failed. That's a different failure mode than a 4xx/5xx
 * response, and needs a message that doesn't just parrot the browser's raw
 * "NetworkError when attempting to fetch resource" / "Failed to fetch" text.
 */
async function safeFetch(url, opts) {
  try {
    return await fetch(url, opts);
  } catch {
    const err = new Error("SERVER_UNREACHABLE");
    // Which server we actually dialled is the one fact worth having here. The
    // URL comes out of roamingSettings, set by whoever last connected this
    // mailbox, so it is regularly not the server the person reading the error
    // assumes it is - and "check the URL" is unhelpful when it doesn't say which.
    try {
      err.url = new URL(url).origin;
    } catch {
      /* non-absolute URL; the plain message is still correct */
    }
    throw err;
  }
}

/*
 * Odoo type='json' routes speak JSON-RPC 2.0, not plain JSON. Post the envelope
 * or the route silently sees no params. Success comes back as {result: ...}; an
 * unhandled server exception comes back as {error: ...} and still HTTP 200, so
 * res.ok tells you very little. Expected failures - bad password, a token we no
 * longer accept - are reported by the routes as {error: "..."} inside a normal
 * result, precisely so they travel the ordinary dispatch path and arrive with
 * the CORS headers the browser needs before it will let us read them at all.
 */
async function odooRpc(path, params = {}, { auth = true, base = null } = {}) {
  base = base || get("odooUrl");
  if (!base) throw new Error("NOT_CONNECTED");

  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = get("accessToken");
    if (!token) throw new Error("NOT_CONNECTED");
    headers["Authorization"] = "Bearer " + token;
  }

  const res = await safeFetch(base + path, {
    method: "POST",
    headers,
    body: JSON.stringify({ jsonrpc: "2.0", method: "call", params, id: null }),
  });

  if (res.status === 404) {
    // Naming the route that 404'd is what distinguishes "nothing is installed"
    // from "this one newer endpoint is missing", which is the difference
    // between reinstalling and just restarting.
    const err = new Error("MODULE_MISSING");
    err.url = base + path;
    throw err;
  }
  if (!res.ok) throw new Error(`Odoo returned HTTP ${res.status} for ${path}`);

  const payload = await res.json();
  if (payload.error) {
    const d = payload.error.data || {};
    throw new Error(d.message || payload.error.message || "Odoo error");
  }

  // TOKEN_REJECTED matches a key in ERROR_MESSAGES and is what the callers
  // watch for to drop the mailbox back to the connect form; anything else the
  // routes put here is already a finished sentence meant for the user.
  const result = payload.result;
  if (result && result.error) throw new Error(result.error);
  return result;
}

/* ------------------------------------------------------------------- auth */

async function connect({ login, password, url, db }) {
  const origin = normalizeOdooUrl(url);

  // auth: false because there is no token yet - this call is what mints one.
  const result = await odooRpc(
    "/aktiv/auth/login",
    { login, password, db: db || undefined },
    { auth: false, base: origin }
  );

  // A rejected login already threw out of odooRpc with the route's own wording.
  if (!result || !result.access_token) {
    throw new Error("Odoo did not return an access token.");
  }

  set("odooUrl", origin);
  set("odooLogin", login);
  set("accessToken", result.access_token);
  await saveSettings();
}

/*
 * `reason` is the error key that forced the disconnect, if any. Without it the
 * panel would silently drop back to a login form with no account of itself,
 * which reads like the add-in lost its place rather than like Odoo turned the
 * token down.
 */
async function disconnect(reason) {
  set("accessToken", null);
  await saveSettings();
  showConnect();
  if (reason) {
    // showConnect() hid #error on its way past; put it back underneath the form.
    const el = document.getElementById("error");
    el.textContent = ERROR_MESSAGES[reason] || reason;
    el.classList.remove("hidden");
  }
}

/* --------------------------------------------------------------- licensing */

/*
 * Our only chokepoint. Because we are not in the Outlook<->Odoo data path, the
 * licence check has to be something the taskpane asks for on load.
 *
 * getAccessTokenAsync returns a JWT for the signed-in M365 user, issued by Azure
 * AD against the WebApplicationInfo block in manifest.xml. Validate it
 * server-side (signature, aud, iss) and key the subscription on the `tid`
 * tenant claim. Do NOT trust anything the client says about its own licence.
 */
function getOfficeIdentityToken() {
  return new Promise((resolve, reject) => {
    Office.auth.getAccessTokenAsync({ allowSignInPrompt: true }, (r) =>
      r.status === Office.AsyncResultStatus.Succeeded ? resolve(r.value) : reject(r.error)
    );
  });
}

async function checkLicense() {
  // See config.js. Lets you test the Odoo handshake before Azure AD exists.
  if (CFG.DEV_SKIP_LICENSE) {
    console.warn("[Aktiv] DEV_SKIP_LICENSE is on — licence check bypassed. Do not ship.");
    return { active: true, plan: "dev", expires: null };
  }

  const idToken = await getOfficeIdentityToken();
  const res = await safeFetch(`${ADDIN_ORIGIN}/api/license`, {
    method: "POST",
    headers: { Authorization: "Bearer " + idToken },
  });
  if (!res.ok) throw new Error("Could not verify your licence. Try again shortly.");
  return res.json(); // { active: bool, plan: string, expires: string }
}

/* -------------------------------------------------------------------- flow */

function show(id) {
  ["loading", "connect-form", "body", "status", "error"].forEach((x) =>
    document.getElementById(x).classList.toggle("hidden", x !== id)
  );
}

function showConnect() {
  const knownUrl = get("odooUrl");
  const knownLogin = get("odooLogin");
  if (knownUrl) document.getElementById("odoo-url").value = knownUrl;
  if (knownLogin) document.getElementById("odoo-login").value = knownLogin;
  show("connect-form");
}

const ERROR_MESSAGES = {
  NOT_CONNECTED: "Connect your Odoo server to continue.",
  // A 404 here means the route isn't in that server's routing map. Missing
  // module is one cause; an older copy of Aktiv Outlook Plugin that predates the
  // route is just as common, and reads identically from the browser - so say
  // both rather than sending people to check an install that is already fine.
  MODULE_MISSING: "That Odoo server doesn't recognise this request. Mail Plugin and Aktiv Outlook Plugin must both be installed, and the plugin must be up to date — a server still running an older copy won't have the newer routes, and needs restarting after an update.",
  TOKEN_REJECTED: "Your Odoo access has expired or was revoked. Please reconnect.",
  SERVER_UNREACHABLE: "Couldn't reach that Odoo server. Check the URL, that it's running and reachable over HTTPS, and that CORS is enabled for this add-in (see TESTING.md).",
  NO_SUBJECT: "Add a subject to this email first — it becomes the name of the record.",
};

// #error is white-space: pre-wrap, so the appended line breaks render.
function errorText(e) {
  const base = ERROR_MESSAGES[e.message] || e.message || String(e);
  return e.url ? `${base}\n\nTried: ${e.url}` : base;
}

// Used by the connect/boot flow, before there's a working panel to keep visible.
function showError(e) {
  document.getElementById("error").textContent = errorText(e);
  show("error");
}

// Used once the panel is up (e.g. a failed Create Lead click) - shows the
// error alongside the existing buttons instead of hiding them.
function showInlineError(e) {
  const el = document.getElementById("error");
  el.textContent = errorText(e);
  el.classList.remove("hidden");
}

function showStatus(text) {
  const el = document.getElementById("status");
  el.textContent = text;
  el.classList.remove("hidden");
}

async function onConnectSubmit(ev) {
  ev.preventDefault();
  show("loading");
  try {
    await connect({
      login: document.getElementById("odoo-login").value,
      password: document.getElementById("odoo-password").value,
      url: document.getElementById("odoo-url").value,
      db: document.getElementById("odoo-db").value,
    });
    await boot();
  } catch (e) {
    if (e.message === "TOKEN_REJECTED") return disconnect(e.message);
    showError(e);
  }
}

async function boot() {
  show("loading");
  if (!get("odooUrl") || !get("accessToken")) return showConnect();
  try {
    const lic = await checkLicense();
    if (!lic.active) throw new Error("Your Aktiv subscription is inactive.");
    await renderHook();
    show("body");
  } catch (e) {
    if (e.message === "TOKEN_REJECTED") return disconnect(e.message);
    showError(e);
  }
}

/* ------------------------------------------------------------- email data */

/*
 * Read mode hands back plain values - item.subject is a string, item.from is an
 * object with .emailAddress on it. Compose mode hands back accessor objects for
 * the same names - item.subject.getAsync, item.to.getAsync - because the user is
 * still typing and there is no settled value to read synchronously. Every field
 * this panel touches differs that way, so branch on it once, here, rather than
 * at each call site. Reading item.subject.getAsync is the cheapest tell.
 */
function isCompose() {
  const subject = Office.context.mailbox.item.subject;
  return !!subject && typeof subject.getAsync === "function";
}

// Office.js async methods all take their callback last and report through
// AsyncResult. One wrapper beats six hand-rolled promise constructors.
function officeAsync(thisArg, method, ...args) {
  return new Promise((resolve, reject) => {
    method.call(thisArg, ...args, (r) =>
      r.status === Office.AsyncResultStatus.Succeeded ? resolve(r.value) : reject(r.error)
    );
  });
}

function getItemBodyHtml() {
  // body.getAsync is the same call in both modes.
  const body = Office.context.mailbox.item.body;
  return officeAsync(body, body.getAsync, Office.CoercionType.Html);
}

function getSubject() {
  const item = Office.context.mailbox.item;
  if (!isCompose()) return Promise.resolve(item.subject);
  return officeAsync(item.subject, item.subject.getAsync);
}

/*
 * Who the record gets filed against. Reading, that is whoever wrote to you.
 * Composing, you are the sender - so the useful contact is the first person you
 * are writing to, which is also the one that may still be empty when the panel
 * opens on a blank new mail.
 */
async function getContact() {
  const item = Office.context.mailbox.item;

  if (!isCompose()) {
    const from = item.from || item.sender || {};
    return { email: from.emailAddress, name: from.displayName || from.emailAddress };
  }

  const to = (await officeAsync(item.to, item.to.getAsync)) || [];
  const first = to[0];
  return first
    ? { email: first.emailAddress, name: first.displayName || first.emailAddress }
    : {};
}

function getAttachmentContent(id) {
  const item = Office.context.mailbox.item;
  return officeAsync(item, item.getAttachmentContentAsync, id);
}

// Only real files, not inline images already part of the body, and only
// Base64 content - Office.js also hands back Eml/ICalendar/Url formats for
// some attachment types, which the backend has no use for here.
async function getRealAttachments() {
  const item = Office.context.mailbox.item;

  let details;
  if (!isCompose()) {
    details = item.attachments || [];
  } else if (typeof item.getAttachmentsAsync === "function") {
    // Mailbox 1.8. The manifest still asks for only 1.3, so on an older client
    // we create the record without the files rather than refuse to create it.
    details = (await officeAsync(item, item.getAttachmentsAsync)) || [];
  } else {
    return [];
  }

  const real = details.filter((a) => !a.isInline);
  if (!real.length) return [];

  // getAttachmentContentAsync reads from the copy on the server. A draft's
  // attachments only exist there once the draft has been saved.
  if (isCompose()) await officeAsync(item, item.saveAsync);

  const out = [];
  for (const a of real) {
    const content = await getAttachmentContent(a.id);
    if (content.format !== Office.MailboxEnums.AttachmentContentFormat.Base64) continue;
    // AttachmentDetailsCompose carries no contentType - only read mode has one.
    // The backend guesses from the filename when this is missing.
    out.push({ name: a.name, mimetype: a.contentType, content: content.content });
  }
  return out;
}

/* --------------------------------------------------------- sending a draft */

/*
 * Whether the panel can send the draft itself, which is what turns "file it,
 * then go and press Send" into one button.
 *
 * item.sendAsync arrived in Mailbox 1.15, so it is present in Outlook on the
 * web, new Outlook for Windows, and classic Outlook for Windows from Version
 * 2412 (Build 18324.20172). It is NOT in Outlook for Mac (which stops at 1.14
 * at the time of writing), in the LTSC builds, or against on-premises Exchange
 * (which caps every client at 1.5). Hence a feature test rather than a manifest
 * requirement: raising the manifest's MinVersion would stop the whole add-in
 * loading on those clients instead of just this one button. The declared
 * requirement set never limits which APIs we may call, only which clients will
 * load us at all, so calling a 1.15 API from a 1.3 manifest is correct and
 * supported - guarded like this.
 *
 * Test for the method rather than isSetSupported('Mailbox', '1.15'): it is the
 * narrower question, it's the technique Microsoft's own docs recommend, and it
 * stays true on a client that ships the API ahead of advertising the whole set.
 */
function canSendFromPanel() {
  return isCompose() && typeof Office.context.mailbox.item.sendAsync === "function";
}

/*
 * Hands the draft to Outlook to send.
 *
 * Careful with anything after this resolves: per the Office docs, once
 * sendAsync succeeds "the add-in that called it ceases running" - the compose
 * surface is gone, so the panel goes with it. Any message the user needs to
 * read has to be on screen BEFORE this is called, not in a .then() after it.
 */
function sendMessage() {
  const item = Office.context.mailbox.item;
  return officeAsync(item, item.sendAsync);
}

/*
 * The one failure worth spelling out, shared by every send-and-file path:
 * Odoo already has the record and then Outlook refused to send.
 *
 * The generic error hides which half failed, and the obvious reaction to "that
 * didn't work" - fix the draft, press the button again - files a second copy
 * or creates a second lead. Say what landed, and that the draft is still
 * theirs to send by hand.
 */
function showSendFailedAfter(whatLanded, e) {
  showInlineError(new Error(
    `${whatLanded}, but Outlook wouldn't send the email: ${e.message || e}` +
    `\n\nIt is already in Odoo — don't do it again. Press Send in Outlook ` +
    `when you're ready.`
  ));
}

/* ==========================================================================
 * THE HOOK - the only part of this file that depends on what you're selling.
 * ========================================================================== */
/*
 * Which Odoo this mailbox is wired to, and the way back out.
 *
 * The URL lives in roamingSettings from whenever someone last connected, so it
 * follows the mailbox across clients and is very easy to lose track of - which
 * is exactly how an unreachable server turns into a hunt through the wrong
 * infrastructure. Showing it costs one line and settles the question.
 *
 * Disconnect is also the answer to "how do I point this at a different
 * server": it drops the stored token and returns to the connect form, where
 * the URL field is pre-filled with the old address for you to type over.
 */
function renderConnectionLine() {
  const wrap = document.createElement("div");
  wrap.id = "connection";

  const login = get("odooLogin");
  const label = document.createElement("span");
  label.textContent = login ? `${get("odooUrl")} — ${login}` : get("odooUrl");
  wrap.appendChild(label);

  const btn = document.createElement("button");
  btn.id = "disconnect-btn";
  btn.type = "button";
  btn.textContent = "Disconnect";
  btn.addEventListener("click", () => disconnect());
  wrap.appendChild(btn);

  return wrap;
}

function actionRow(actions) {
  const row = document.createElement("div");
  for (const [label, onClick] of actions) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = label;
    btn.addEventListener("click", onClick);
    row.appendChild(btn);
  }
  return row;
}

async function renderHook() {
  const el = document.getElementById("body");
  el.innerHTML = "";

  el.appendChild(renderConnectionLine());

  const info = document.createElement("p");
  info.id = "contact-line";
  el.appendChild(info);
  await renderContactLine();

  el.appendChild(actionRow([
    ["Create CRM Lead", () => createFromEmail("lead")],
    ["Create CRM Opportunity", () => createFromEmail("opportunity")],
    ["Create Helpdesk Ticket", () => createFromEmail("ticket")],
  ]));
  el.appendChild(actionRow([
    ["Add to existing Lead…", () => pickAndAppend("lead")],
    ["Add to existing Ticket…", () => pickAndAppend("ticket")],
  ]));

  // Send-and-file. Only on a draft (there is nothing to send while reading),
  // and only where Outlook will let us send it - see canSendFromPanel.
  if (isCompose()) {
    if (canSendFromPanel()) {
      // Mirrors the two rows above - create vs. file onto something that
      // already exists - so the send half offers the same choice rather than
      // dead-ending on "No leads found" for a customer new to Odoo.
      const newRow = actionRow([
        ["Send & create Lead", () => createFromEmail("lead", { send: true })],
        ["Send & create Opportunity", () => createFromEmail("opportunity", { send: true })],
        ["Send & create Ticket", () => createFromEmail("ticket", { send: true })],
      ]);
      newRow.className = "send-row";
      el.appendChild(newRow);

      el.appendChild(actionRow([
        ["Send & add to Lead…", () => pickAndAppend("lead", { send: true })],
        ["Send & add to Ticket…", () => pickAndAppend("ticket", { send: true })],
      ]));
    } else {
      // Say which clients do have it, because "your Outlook is too old" with no
      // number is the kind of message that comes straight back as a support
      // ticket. The buttons above still work; this only costs the extra click.
      const note = document.createElement("p");
      note.className = "muted";
      note.textContent =
        "Sending from this panel needs Outlook on the web, new Outlook for " +
        "Windows, or Outlook 2412 or later. Add this mail to a record above, " +
        "then press Send as usual.";
      el.appendChild(note);
    }
  }

  // The match list is drawn on demand and torn down after; keeping it in its
  // own node means the buttons above never get rebuilt underneath the user.
  const picker = document.createElement("div");
  picker.id = "picker";
  el.appendChild(picker);

  // Composing, the panel is often opened on a blank new mail before the To line
  // has been filled in (and the recipient can change after that). Without this
  // the contact line would sit there stale, saying nobody is on the mail while
  // the user looks at the name they just typed. Mailbox 1.7, so feature-detect.
  if (isCompose() && Office.EventType.RecipientsChanged &&
      typeof Office.context.mailbox.item.addHandlerAsync === "function") {
    Office.context.mailbox.item.addHandlerAsync(
      Office.EventType.RecipientsChanged,
      renderContactLine,
      // The panel still works without live refresh, so a failure here is not
      // worth tearing the whole thing down over.
      (r) => {
        if (r.status !== Office.AsyncResultStatus.Succeeded) {
          console.warn("[Aktiv] RecipientsChanged unavailable:", r.error);
        }
      }
    );
  }
}

async function renderContactLine() {
  const el = document.getElementById("contact-line");
  if (!el) return;

  const contact = await getContact();
  if (contact.email) {
    el.className = "";
    el.textContent = `${isCompose() ? "To" : "From"}: ${contact.name} <${contact.email}>`;
  } else {
    el.className = "muted";
    el.textContent = "No recipient yet — the record will be created without a contact.";
  }
}

/*
 * Make a new lead or ticket from the open mail. With {send: true} the draft
 * goes out in the same click - the counterpart of appendToRecord's send, for
 * the customer who has nothing in Odoo yet, which is exactly when the picker
 * says "No leads found" and there is otherwise nowhere to go.
 *
 * Same order as appendToRecord, for the same reason: create first, send
 * second. A refused create leaves the draft intact to retry; sending first
 * would put mail in front of the customer with no record of it.
 */
async function createFromEmail(kind, { send = false } = {}) {
  show("body"); // keep the buttons visible while we work
  document.getElementById("status").classList.add("hidden");
  document.getElementById("error").classList.add("hidden");

  let created = null;
  try {
    // Read fresh rather than reusing what renderHook() showed - composing, the
    // subject and recipient can have changed since the panel was drawn.
    const [subject, contact, body] = await Promise.all([
      getSubject(),
      getContact(),
      getItemBodyHtml(),
    ]);

    // crm.lead.name and helpdesk.ticket.name are both required, so an untitled
    // draft would come back as a bare server traceback. Check before the
    // attachment step, which saves the draft as a side effect.
    if (!subject || !subject.trim()) throw new Error("NO_SUBJECT");

    const attachments = await getRealAttachments();

    // Lead and opportunity share one route (and one model); lead_type is the
    // only difference between them.
    const isCrm = kind === "lead" || kind === "opportunity";
    const path = isCrm ? "/aktiv/lead/create" : "/aktiv/helpdesk/create";
    const params = {
      subject,
      email: contact.email,
      name: contact.name,
      body,
      attachments,
    };
    if (isCrm) params.lead_type = kind;
    const result = await odooRpc(path, params);

    created = {
      lead: `Lead created (#${result.id})`,
      opportunity: `Opportunity created (#${result.id})`,
      ticket: `Helpdesk ticket created (#${result.id})`,
    }[kind];

    if (!send) {
      showStatus(`${created}.`);
      return;
    }

    // On screen before sendAsync, never after - a successful send takes the
    // compose surface, and this panel, away with it.
    showStatus(`${created}. Sending…`);
    await sendMessage();
  } catch (e) {
    if (e.message === "TOKEN_REJECTED") return disconnect(e.message);
    if (created) return showSendFailedAfter(created, e);
    showInlineError(e);
  }
}

/* ------------------------------------------------- add to existing record */

const KIND_NOUN = { lead: "lead", ticket: "ticket" };

function hide(id) {
  document.getElementById(id).classList.add("hidden");
}

function clearPicker() {
  const picker = document.getElementById("picker");
  if (picker) picker.innerHTML = "";
}

/*
 * Filing the open email onto something that already exists, rather than making
 * a third near-duplicate lead for a thread that is already being worked. The
 * server matches on the sender's address, so the list is usually short enough
 * to pick from at a glance.
 */
async function pickAndAppend(kind, { send = false } = {}) {
  show("body");
  hide("error");
  hide("status");
  clearPicker();

  try {
    const contact = await getContact();
    await searchAndRenderPicker(kind, { email: contact.email }, contact, { send });
  } catch (e) {
    hide("status");
    if (e.message === "TOKEN_REJECTED") return disconnect(e.message);
    showInlineError(e);
  }
}

/*
 * Runs one /aktiv/record/search and redraws the picker with what comes back.
 * Shared by the initial address-matched search and every re-search the
 * picker's own search box kicks off, so a typed name renders exactly the
 * same way an address match does.
 */
async function searchAndRenderPicker(kind, params, contact, { send = false } = {}) {
  try {
    showStatus("Searching…");
    const res = await odooRpc("/aktiv/record/search", { kind, ...params });
    hide("status");
    renderPicker(kind, res.records || [], contact, { send, searchTerm: params.query || "" });
  } catch (e) {
    hide("status");
    if (e.message === "TOKEN_REJECTED") return disconnect(e.message);
    showInlineError(e);
  }
}

function renderPicker(kind, records, contact, { send = false, searchTerm = "" } = {}) {
  const picker = document.getElementById("picker");
  picker.innerHTML = "";
  const who = contact.email || "this message";

  // Typing a name works whether or not the address match found anything - on
  // a compose draft with no recipient yet it is the only way in at all, and
  // it is usually faster than scanning an address-matched list on a reply.
  const searchRow = document.createElement("div");
  searchRow.className = "picker-search";
  const searchInput = document.createElement("input");
  searchInput.type = "text";
  searchInput.placeholder = `Search ${KIND_NOUN[kind]}s by name…`;
  searchInput.value = searchTerm;
  const searchBtn = document.createElement("button");
  searchBtn.type = "button";
  searchBtn.textContent = "Search";
  const runSearch = () => {
    const q = searchInput.value.trim();
    if (q) searchAndRenderPicker(kind, { query: q }, contact, { send });
  };
  searchBtn.addEventListener("click", runSearch);
  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      runSearch();
    }
  });
  searchRow.appendChild(searchInput);
  searchRow.appendChild(searchBtn);
  picker.appendChild(searchRow);

  const head = document.createElement("p");
  head.className = "muted";
  if (!records.length) {
    head.textContent = searchTerm
      ? `No ${KIND_NOUN[kind]}s found for "${searchTerm}".`
      : `No ${KIND_NOUN[kind]}s found for ${who}.`;
  } else if (send) {
    // Spell out that picking a row is the irreversible bit. These rows look
    // exactly like the ones that only file a copy, and the difference here is
    // that the mail leaves the building.
    head.textContent =
      `Pick a ${KIND_NOUN[kind]} for ${who} — the email is filed onto it and sent:`;
  } else {
    head.textContent = searchTerm
      ? `Matching ${KIND_NOUN[kind]}s for "${searchTerm}" — pick one:`
      : `Matching ${KIND_NOUN[kind]}s for ${who} — pick one:`;
  }
  picker.appendChild(head);

  for (const record of records) {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "picker-row";
    // Stage is what separates two rounds of the same conversation; the label
    // is what separates a lead from an opportunity, which share a model.
    row.textContent = [record.name, record.kind_label, record.stage]
      .filter(Boolean)
      .join(" — ");
    row.addEventListener("click", () => appendToRecord(kind, record.id, { send }));
    picker.appendChild(row);
  }

  // Nothing matched, which for a customer who is new to Odoo is the normal
  // case, not an error - and it used to end the flow with no way forward.
  // Offer the thing they came here to do, carrying the send choice with it.
  if (!records.length) {
    const create = document.createElement("button");
    create.type = "button";
    create.className = "picker-row";
    create.textContent = send
      ? `Create a new ${KIND_NOUN[kind]} and send`
      : `Create a new ${KIND_NOUN[kind]}`;
    create.addEventListener("click", () => {
      clearPicker();
      createFromEmail(kind, { send });
    });
    picker.appendChild(create);
  }

  // Always offered: the empty list needs dismissing as much as a full one.
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.className = "linkish";
  cancel.textContent = "Cancel";
  cancel.addEventListener("click", clearPicker);
  picker.appendChild(cancel);
}

/*
 * File the open mail onto an existing record, and - with {send: true} - hand
 * the draft to Outlook to send in the same click.
 *
 * Order matters: file first, send second. Odoo is the step that can fail in a
 * way we can still do something about; if the append is refused, the draft is
 * untouched and sitting there to retry. Sending first would mean a failed
 * append leaves a mail already gone to the customer with nothing on the record,
 * which is the exact silent gap this feature exists to close.
 */
async function appendToRecord(kind, id, { send = false } = {}) {
  clearPicker();
  hide("error");
  showStatus(send ? "Adding to Odoo…" : "Adding…");

  let filed = null;
  try {
    // Read fresh, for the reason createFromEmail does: on a compose draft the
    // subject and body can have moved on since the picker was drawn. No
    // NO_SUBJECT check here though - we are naming nothing, just posting a note.
    const [subject, contact, body] = await Promise.all([
      getSubject(),
      getContact(),
      getItemBodyHtml(),
    ]);
    const attachments = await getRealAttachments();

    // The contact goes up so the note can say who actually wrote the mail - the
    // chatter credits the API key's user as author, not the sender. Composing,
    // that contact is the recipient rather than the sender, so the direction
    // goes up too or the note heads a mail we are sending with "From: <the
    // customer>", crediting them with something they have not written.
    const result = await odooRpc("/aktiv/record/append", {
      kind,
      id,
      subject,
      email: contact.email,
      name: contact.name,
      body,
      attachments,
      direction: isCompose() ? "outgoing" : "incoming",
    });

    filed = result.name;

    if (!send) {
      showStatus(`Added to ${result.name}.`);
      return;
    }

    // On screen before sendAsync, never after: a successful send tears down the
    // compose surface and this panel with it, so anything queued for afterwards
    // may simply never run. This line is the user's only receipt.
    showStatus(`Added to ${result.name}. Sending…`);
    await sendMessage();
  } catch (e) {
    hide("status");
    if (e.message === "TOKEN_REJECTED") return disconnect(e.message);

    // Which half failed changes what the user should do next - see
    // showSendFailedAfter for why the filed-then-send-failed case gets its own
    // wording rather than the bare Outlook error.
    if (filed) return showSendFailedAfter(`The email was added to ${filed}`, e);
    showInlineError(e);
  }
}
