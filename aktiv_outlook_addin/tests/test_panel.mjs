/*
 * Drives the real taskpane.js against the real Odoo, stubbing only the two
 * things node hasn't got: Office.js and the DOM.
 *
 * This is the closest we can get to the send-and-file button without Outlook.
 * It cannot prove sendAsync works in a real client - only Outlook can - but it
 * does prove the panel calls it, calls it in the right order relative to Odoo,
 * and says the right thing when it fails.
 *
 *   node test_panel.mjs [http://localhost:8019] [aktiv_addin_test]
 */
import { readFileSync } from "node:fs";
import vm from "node:vm";

import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ODOO = process.argv[2] || "http://localhost:8019";
const DB = process.argv[3] || "aktiv_addin_test";
// Credentials from the environment, never defaulted to admin/admin: this test
// mints a real API key against a real user, and a script that quietly works
// with the default password is a script that encourages leaving it in place.
const LOGIN = process.env.Aktiv_LOGIN;
const PASSWORD = process.env.Aktiv_PASSWORD;
if (!LOGIN || !PASSWORD) {
  console.error("Set Aktiv_LOGIN and Aktiv_PASSWORD (an internal Odoo user on that database).\n" +
                "  Aktiv_LOGIN=admin Aktiv_PASSWORD=... node test_panel.mjs [url] [db]");
  process.exit(2);
}
const ADDIN = join(dirname(fileURLToPath(import.meta.url)), "..", "taskpane.js");
const CONTACT = { email: "sarah.miller@northwind-eng.test", name: "Sarah Miller" };

let failures = [];
const check = (label, ok, detail = "") => {
  console.log((ok ? "  PASS  " : "  FAIL  ") + label + (!ok && detail ? `\n          ${detail}` : ""));
  if (!ok) failures.push(label);
};

/* ------------------------------------------------------------- DOM stub */
class El {
  constructor(tag) {
    this.tag = tag; this.children = []; this.handlers = {};
    this._text = ""; this._cls = new Set(); this.type = "";
    const self = this;
    this.classList = {
      add: (c) => self._cls.add(c),
      remove: (c) => self._cls.delete(c),
      contains: (c) => self._cls.has(c),
      toggle: (c, on) => (on === undefined ? (self._cls.has(c) ? self._cls.delete(c) : self._cls.add(c)) : (on ? self._cls.add(c) : self._cls.delete(c))),
    };
  }
  set id(v) { this._id = v; if (this._reg) this._reg.set(v, this); }
  get id() { return this._id; }
  set className(v) { this._cls = new Set(String(v).split(/\s+/).filter(Boolean)); }
  get className() { return [...this._cls].join(" "); }
  set textContent(v) { this._text = String(v); this.children = []; }
  get textContent() { return this._text; }
  set innerHTML(v) { if (v === "") { this.children = []; this._text = ""; } }
  appendChild(c) { this.children.push(c); return c; }
  addEventListener(ev, fn) { (this.handlers[ev] ||= []).push(fn); }
  click() { return Promise.all((this.handlers.click || []).map((f) => f())); }
  get hidden() { return this._cls.has("hidden"); }
  // Depth-first text of this node and everything under it.
  all() { return [this, ...this.children.flatMap((c) => c.all())]; }
  find(pred) { return this.all().find(pred); }
}
/* A fresh DOM per load. Shared state here let one panel's async render keep
   appending into the next test's #body, which produced a phantom "the send row
   is drawn when sendAsync is missing" - a harness bug that looked like a code
   bug. Isolate, or the failures are not about the code. */
function makeDom() {
  const byId = new Map();
  const document = {
    getElementById: (id) => byId.get(id) || null,
    createElement: (tag) => { const e = new El(tag); e._reg = byId; return e; },
  };
  const mk = (id) => { const e = new El("div"); e._reg = byId; e.id = id; return e; };
  ["loading", "connect-form", "body", "status", "error"].forEach(mk);
  ["odoo-url", "odoo-login", "odoo-password", "odoo-db"].forEach((i) => { mk(i).value = ""; });
  return { byId, document };
}

/* ---------------------------------------------------------- Office stub */
const OK = "succeeded", ERR = "failed";
const ok = (v) => ({ status: OK, value: v });

function makeOffice({ compose, withSendAsync = true, sendFails = false, store }) {
  const sent = { called: false };
  const item = compose
    ? {
        subject: { getAsync: (cb) => cb(ok("Your quote, as promised")) },
        to: { getAsync: (cb) => cb(ok([{ emailAddress: CONTACT.email, displayName: CONTACT.name }])) },
        body: { getAsync: (_t, cb) => cb(ok('<p>Here is the quote.</p><img src="cid:sig01">')) },
        saveAsync: (cb) => cb(ok("draftid")),
        getAttachmentsAsync: (cb) => cb(ok([{ id: "a1", name: "quote.pdf", isInline: false }])),
        getAttachmentContentAsync: (_id, cb) => cb(ok({ format: "base64", content: "JVBERi0xLjQK" })),
        addHandlerAsync: (_e, _h, cb) => cb(ok()),
      }
    : {
        subject: "Re: your enquiry",
        from: { emailAddress: CONTACT.email, displayName: CONTACT.name },
        body: { getAsync: (_t, cb) => cb(ok("<p>Any update?</p>")) },
        attachments: [],
      };
  if (compose && withSendAsync) {
    item.sendAsync = (cb) => {
      sent.called = true;
      cb(sendFails ? { status: ERR, error: { message: "No recipient specified." } } : ok());
    };
  }
  return {
    sent,
    Office: {
      HostType: { Outlook: "Outlook" },
      AsyncResultStatus: { Succeeded: OK, Failed: ERR },
      CoercionType: { Html: "html" },
      MailboxEnums: { AttachmentContentFormat: { Base64: "base64" } },
      EventType: { RecipientsChanged: "RecipientsChanged" },
      context: {
        roamingSettings: {
          get: (k) => store[k],
          set: (k, v) => { store[k] = v; },
          saveAsync: (cb) => cb({ status: OK }),
        },
        mailbox: { item },
      },
      onReady(cb) { this._ready = cb; },
    },
  };
}

/* ------------------------------------------------------------ load panel */
async function loadPanel(opts) {
  const { byId, document } = makeDom();
  const { Office, sent } = makeOffice(opts);
  const ctx = vm.createContext({
    Office, document, console, fetch, URL, Promise, JSON, String, Error,
    setTimeout, location: { origin: "https://addin.test" },
    window: { AKTIV_CONFIG: { DEV_SKIP_LICENSE: true } },
  });
  vm.runInContext(readFileSync(ADDIN, "utf8"), ctx, { filename: "taskpane.js" });
  await Office._ready({ host: "Outlook" });          // runs boot() -> renderHook()
  // #picker is the last node renderHook appends, so its presence means the
  // render finished - waiting on "body has any child" samples mid-render.
  await until(() => byId.get("picker"));
  return { ctx, sent, byId, body: byId.get("body"), status: byId.get("status"), error: byId.get("error") };
}

async function until(pred, ms = 8000) {
  for (let i = 0; i < ms / 25; i++) { if (pred()) return true; await new Promise((r) => setTimeout(r, 25)); }
  return false;
}

const labels = (root) => root.all().filter((e) => e.tag === "button").map((e) => e.textContent);
const btn = (root, text) => root.find((e) => e.tag === "button" && e.textContent === text);

/* ------------------------------------------------------------------ run */
const rpc = async (path, params, token) => {
  const r = await fetch(ODOO + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}) },
    body: JSON.stringify({ jsonrpc: "2.0", method: "call", params, id: null }),
  });
  const p = await r.json();
  if (p.error) throw new Error(JSON.stringify(p.error).slice(0, 400));
  return p.result;
};

const auth = await rpc("/aktiv/auth/login", { login: LOGIN, password: PASSWORD, db: DB });
if (!auth.access_token) throw new Error("login failed: " + JSON.stringify(auth));
const store = { odooUrl: ODOO, odooLogin: "admin", accessToken: auth.access_token };
const noteCount = async (id) =>
  (await rpc("/aktiv/record/search", { kind: "lead", email: CONTACT.email }, auth.access_token)).records.length;

console.log("\n--- the Send & row appears only where it can work ---");
let p = await loadPanel({ compose: true, withSendAsync: true, store });
check("compose + sendAsync: send row is drawn",
  labels(p.body).includes("Send & add to Lead…") && labels(p.body).includes("Send & add to Ticket…"),
  labels(p.body).join(" | "));

p = await loadPanel({ compose: false, store });
check("read mode: no send row (nothing to send)",
  !labels(p.body).some((l) => l.startsWith("Send &")), labels(p.body).join(" | "));

p = await loadPanel({ compose: true, withSendAsync: false, store });
check("compose without sendAsync: no send row",
  !labels(p.body).some((l) => l.startsWith("Send &")), labels(p.body).join(" | "));
check("compose without sendAsync: names the clients that have it",
  !!p.body.find((e) => e._text.includes("Outlook 2412 or later")),
  p.body.all().map((e) => e._text).filter(Boolean).join(" | "));

console.log("\n--- picking a record files it AND sends, in that order ---");
p = await loadPanel({ compose: true, withSendAsync: true, store });
await btn(p.body, "Send & add to Lead…").click();
await until(() => p.byId.get("picker").children.length);
const picker = p.byId.get("picker");
const rows = picker.all().filter((e) => e.className.includes("picker-row"));
check("picker warns that this one sends",
  picker.children[0]._text.includes("filed onto it and sent"), picker.children[0]._text);
check("rows separate a Lead from an Opportunity",
  rows.some((r) => r.textContent.includes("— Opportunity —")) && rows.some((r) => r.textContent.includes("— Lead —")),
  rows.map((r) => r.textContent).join(" | "));

const opp = rows.find((r) => r.textContent.includes("— Opportunity —"));
await opp.click();
await until(() => p.sent.called);
check("the draft was handed to Outlook to send", p.sent.called);
check("the user saw it was filed before it sent",
  p.status.textContent.includes("Sending…") && p.status.textContent.includes("Added to"),
  p.status.textContent);
check("no error shown on the happy path", p.error.hidden, p.error.textContent);

console.log("\n--- send & create: the path for a customer new to Odoo ---");
p = await loadPanel({ compose: true, withSendAsync: true, store });
check("send & create buttons are drawn",
  labels(p.body).includes("Send & create Lead") && labels(p.body).includes("Send & create Ticket"),
  labels(p.body).join(" | "));

await btn(p.body, "Send & create Lead").click();
await until(() => p.sent.called);
check("send & create hands the draft to Outlook", p.sent.called);
check("send & create reports the new lead id before sending",
  /Lead created \(#\d+\)\. Sending…/.test(p.status.textContent), p.status.textContent);
check("send & create shows no error", p.error.hidden, p.error.textContent);

console.log("\n--- 'No leads found' must not be a dead end ---");
p = await loadPanel({ compose: true, withSendAsync: true, store });
await btn(p.body, "Send & add to Lead…").click();
await until(() => p.byId.get("picker").children.length);
// Search on an address with nothing behind it.
p.ctx.renderPicker("lead", [], { email: "nobody@example.invalid" }, { send: true });
const empty = p.byId.get("picker");
check("the empty picker offers to create and send",
  !!empty.all().find((e) => e.textContent === "Create a new lead and send"),
  empty.all().map((e) => e.textContent).filter(Boolean).join(" | "));
check("the empty picker can be dismissed",
  !!empty.all().find((e) => e.textContent === "Cancel"),
  empty.all().map((e) => e.textContent).filter(Boolean).join(" | "));

p.ctx.renderPicker("lead", [], { email: "nobody@example.invalid" }, { send: false });
check("without send it offers plain create",
  !!p.byId.get("picker").all().find((e) => e.textContent === "Create a new lead"),
  p.byId.get("picker").all().map((e) => e.textContent).filter(Boolean).join(" | "));

console.log("\n--- a send that fails after the record landed must say so ---");
p = await loadPanel({ compose: true, withSendAsync: true, sendFails: true, store });
await btn(p.body, "Send & add to Lead…").click();
await until(() => p.byId.get("picker").children.length);
const row2 = p.byId.get("picker").all().find((e) => e.className.includes("picker-row"));
// Derive the expected name from the row actually clicked. Hardcoding one made
// this fail the moment another test seeded a lead that sorted above it.
const pickedName = row2.textContent.split(" — ")[0];
await row2.click();
await until(() => !p.byId.get("error").hidden);
const err = p.byId.get("error").textContent;
check("the error names the record it already filed to",
  err.includes(`added to ${pickedName}`), `picked ${pickedName!==undefined?JSON.stringify(pickedName):""} / got: ${err}`);
check("the error says not to do it again", /don't do it again/i.test(err), err);
check("the error passes on what Outlook said", err.includes("No recipient specified."), err);

p = await loadPanel({ compose: true, withSendAsync: true, sendFails: true, store });
await btn(p.body, "Send & create Lead").click();
await until(() => !p.byId.get("error").hidden);
const cerr = p.byId.get("error").textContent;
check("send & create failing names the lead it already created",
  /Lead created \(#\d+\)/.test(cerr), cerr);
check("send & create failing warns against doing it twice",
  /don't do it again/i.test(cerr), cerr);

console.log("\n" + "=".repeat(60));
if (failures.length) { console.log(`${failures.length} FAILED:`); failures.forEach((f) => console.log("  - " + f)); process.exit(1); }
console.log("All panel checks passed.");
