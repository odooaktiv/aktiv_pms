# Testing this locally

You're on Linux, so there is no Outlook desktop client. Everything below targets
**Outlook on the web** — which is the easier loop anyway, since the taskpane is
just an iframe your own browser loads. That means `https://localhost:3000` works
fine as the add-in origin; nothing of yours needs to be publicly reachable.

Your **Odoo** does need to be reachable over **https** though — the taskpane is
https, so a plain-http Odoo is blocked as mixed content. That's what ngrok is for.

Work the phases in order. Phase 1 needs no Outlook at all and catches most of
what actually goes wrong.

---

## Phase 1 — Odoo side only (no Outlook, no add-in)

### 1.1 Fresh test DB with the plugin modules

Never test this against a shared staging DB — the handshake mints real API keys
against real users.

```bash
cd /home/odoo/workspace/19
./17env/bin/python odoo/odoo-bin -c odoo.conf \
  -d addin_test --init base,aktiv_outlook_plugin --stop-after-init
```

`aktiv_outlook_plugin` depends on `mail_plugin`, `crm` and `helpdesk`, so initialising
it pulls all three in. `helpdesk` is Enterprise — it comes from `odoo_ee`, which
`odoo.conf`'s `addons_path` already includes, along with `Aktiv-Demo` itself.

### 1.2 A conf that works behind a tunnel

Your `odoo.conf` has `proxy_mode = False`. Behind ngrok that makes Odoo build
redirect URLs as `http://`, which breaks the auth bounce with a redirect loop or
a mixed-content block. Don't edit the shared conf — make a test one:

```bash
cd /home/odoo/workspace/19
sed 's/^proxy_mode *=.*/proxy_mode = True/' odoo.conf > odoo-addin-test.conf
grep proxy_mode odoo-addin-test.conf   # expect: proxy_mode = True
```

Start it, and open the tunnel in a second terminal:

```bash
./17env/bin/python odoo/odoo-bin -c odoo-addin-test.conf -d addin_test
```
```bash
ngrok http 8019      # note the https://....ngrok-free.app URL
```

**ngrok free interstitial.** The first browser hit on an ngrok URL shows a "You
are about to visit..." click-through. That page will hijack your auth redirect.
Visit the ngrok URL once in the same browser and click **Visit Site** — it sets a
cookie and subsequent navigations pass straight through.

### 1.3 Smoke-test the endpoints with curl

This validates the module, the JSON-RPC envelope, and CORS in one go, before
Outlook is anywhere near it.

```bash
ODOO=https://YOUR-ID.ngrok-free.app

# Is the module installed and reachable?
curl -sS -X POST "$ODOO/mail_plugin/auth/check_version" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"call","params":{},"id":null}'
```

Expect `{"jsonrpc": "2.0", "id": null, "result": 1}`.
A **404** means `mail_plugin` isn't installed on that database.

```bash
# Does CORS preflight actually pass? This is what a reverse proxy silently breaks.
curl -sS -i -X OPTIONS "$ODOO/mail_plugin/auth/check_version" \
  -H 'Origin: https://localhost:3000' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type,authorization' | head -20
```

Expect `200` and an `Access-Control-Allow-Origin: *` header. If that header is
missing, an nginx in front of Odoo is stripping it and **nothing else will work** —
fix it here, not in the JS.

### 1.4 Exercise the create routes without Outlook

Both hooks are reachable with curl, which is the fastest way to prove a backend
change before spending a sideload cycle on it.

```bash
# Mint a token exactly the way the panel's Connect form does.
curl -sS -X POST "$ODOO/aktiv/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"call","params":{
        "login":"admin","password":"admin","db":"addin_test"},"id":null}'
```

```bash
TOKEN=<the access_token from above>

# Attachment with no mimetype - that is what the compose panel sends, because
# AttachmentDetailsCompose has no contentType field. Expect it stored as
# application/pdf, guessed from the filename, not application/octet-stream.
curl -sS -X POST "$ODOO/aktiv/lead/create" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","method":"call","params":{
        "subject":"curl compose test","email":"accounting@lsw-architects.com",
        "name":"LSW Accounting","body":"<p>Test</p>",
        "attachments":[{"name":"quote.pdf","content":"JVBERi0xLjQ="}]},"id":null}'
```

Expect `{"result": {"id": N}}`. Then check the file landed with a real type:

```python
env['ir.attachment'].search([('res_model','=','crm.lead'),('res_id','=',N)]).mapped('mimetype')
```

---

## Phase 2 — Serve the add-in over https

```bash
npx office-addin-dev-certs install     # installs a trusted localhost CA
cd <this-directory>
npx http-server . -S \
  -C ~/.office-addin-dev-certs/localhost.crt \
  -K ~/.office-addin-dev-certs/localhost.key \
  -p 3000
```

Open `https://localhost:3000/taskpane.html` directly in the browser first. It
should load, and the console should show an Office.js error (no host) — that's
expected and means the file is being served with a cert the browser trusts.

**Linux note:** `office-addin-dev-certs` targets the system store; Firefox uses
its own NSS store and may still warn. Either import the CA into Firefox manually
(`~/.office-addin-dev-certs/ca.crt`), or just test in Chrome/Chromium.

`config.js` already points `ADDIN_ORIGIN` at `https://localhost:3000` and has
`DEV_SKIP_LICENSE: true`, so the licence check is bypassed. `manifest.xml` is
already on `https://localhost:3000` throughout and already carries a real
`<Id>` GUID, so neither needs touching for a local run. Both icons and URLs are
in place — if you ever repoint the origin, every URL in the manifest and
`ADDIN_ORIGIN` must move together.

---

## Phase 3 — Sideload into Outlook Web

1. Open Outlook on the web, open any email.
2. **More actions (…) → Get Add-ins → My add-ins**.
3. Under **Custom add-ins**, choose **Add from file…** and pick `manifest.xml`.
4. Accept the warning.

If **Add from file** is missing, your tenant admin has disabled sideloading —
you'll need a tenant where it's permitted. Personal outlook.com accounts don't
reliably offer it; use a Microsoft 365 work account.

**Re-sideloading after a manifest change.** Outlook caches the manifest per
install. Editing `manifest.xml` — adding an extension point, changing a rule —
does nothing until you **remove** the add-in under *My add-ins* and add it from
file again. A compose button that never appears is nearly always this.

Then: open an email → **Open Aktiv** in the ribbon → the panel appears.

### The flow you should see

1. Panel shows the connect form: Username, Password, URL, Database Name.
2. Fill in an **internal** Odoo user, your ngrok URL, and `addin_test` →
   **Connect**. There is no OAuth dialog and no *"Let Aktiv access your Odoo
   database?"* consent screen — `/aktiv/auth/login` posts the credentials straight
   to Odoo and mints the scoped API key itself.
3. Panel shows the contact line and the two Create buttons.

Keep the browser devtools console open on the taskpane iframe throughout.

---

## Phase 3.5 — Compose mode (before the mail is sent)

The panel is registered on both surfaces: `MessageReadCommandSurface` and
`MessageComposeCommandSurface`. Compose is the one with the sharp edges, because
every field comes back as an accessor object rather than a value — see
`isCompose()` in `taskpane.js`.

Open **New email** → **Open Aktiv** on the compose ribbon, then work this table:

| Do this | Expect |
|---|---|
| Open the panel on a blank new mail | `No recipient yet — the record will be created without a contact.` |
| Type an address into **To** | The line switches to `To: Name <addr>` on its own. Driven by the `RecipientsChanged` handler; if it stays stale, that event didn't register — check the console for `RecipientsChanged unavailable`. |
| Click **Create CRM Lead** with no subject | Inline error `Add a subject to this email first…`. No lead in Odoo, and **no draft saved**. |
| Add a subject, click **Create CRM Lead** | `Lead created (#N).` Subject is left exactly as typed — nothing is written back into it. |
| Click **Create CRM Opportunity** | `Opportunity created (#N).` In Odoo it is in the **pipeline** (not Leads), in the first unfolded stage, with you as salesperson and your sales team. |
| Change the **To** after the panel opened, then create | The record files against the *new* recipient. Subject and recipient are re-read at click time, not reused from render. |
| Attach a file, click **Create** | The draft saves itself first (expected — `getAttachmentContentAsync` reads the server-side copy), then the file appears on the lead with a real mimetype, guessed from its name. |
| **Reply** / **Forward** an existing mail | Same panel, To prefilled from the original. |
| Reopen a saved draft from **Drafts** | Same as new mail — `FormType="Edit"` covers drafts too. |
| Open a *received* mail and create a lead | Regression check: the line still reads `From:`, filed against the sender. |

**Composing, the contact is the first To recipient, not you.** You are the sender
on a draft, so `item.from` is your own mailbox and is useless here.

---

## Phase 3.6 — Send & file, in one click

Two rows below the rule, mirroring the two above it — create something new, or
file onto something that exists — except these also send the draft:

```
Send & create Lead       Send & create Opportunity       Send & create Ticket
Send & add to Lead…      Send & add to Ticket…
```

They rest on `item.sendAsync` (**Mailbox 1.15**), which is feature-detected, not
declared in the manifest — see `canSendFromPanel()`. So the rows are present in
Outlook on the web, new Outlook for Windows, and classic Outlook 2412+, and are
replaced by an explanatory line everywhere else. **The manifest is unchanged by
this feature**; there is nothing to re-upload.

Two automated suites cover most of this — see `tests/`. Run them first; this
table is for what only a real client can prove.

| Do this | Expect |
|---|---|
| Open the panel on a **received** mail | No **Send &** rows at all. There is nothing to send while reading. |
| Open a draft on a client below 1.15 (Outlook for Mac, LTSC, any on-prem Exchange) | No **Send &** rows, and the muted line naming the clients that do have it. The other buttons still work. |
| Draft with a recipient → **Send & add to Lead…** | `Searching…`, then the picker headed `Pick a lead for <addr> — the email is filed onto it and sent:` |
| Pick a row | `Adding to Odoo…` → `Added to <name>. Sending…` → the compose window closes and the mail is in **Sent Items**. |
| Then open that record in Odoo | One new internal note, headed **`Sent to: Name <addr>`** — *not* `From:`. Attachments on the note. |
| Same flow with a file attached | The draft saves itself first (as with Create), the file lands on the note, and the mail still sends. |
| **Send & create Lead** on a draft | `Lead created (#N). Sending…` → window closes, mail in **Sent Items**, lead in Odoo with the subject as its name and the recipient as its contact. |
| **Send & create Opportunity** on a draft | `Opportunity created (#N). Sending…` → window closes, mail in **Sent Items**, opportunity in the Odoo pipeline. |
| **Send & create Lead** with no subject | Inline `Add a subject to this email first…`, **nothing created and nothing sent**. The subject check runs before anything else. |
| **Send & add to Lead…** for an address with no leads | `No leads found for <addr>.` plus a **Create a new lead and send** button and a **Cancel**. This must not be a dead end. |
| Click **Create a new lead and send** | Same as **Send & create Lead** — the send choice carries across from the picker. |
| Same, from **Add to existing Lead…** (no send) | The button reads **Create a new lead** and creates without sending. |
| Stop Odoo, then any **Send &** button | Fails with the usual unreachable message and **the draft is not sent**. Odoo is deliberately first, so a dead Odoo can't leak an unrecorded email to the customer. |
| Picker open, then click a row after deleting that lead in Odoo | `That record no longer exists.` and the draft is **not** sent. |
| A lead and an opportunity for the same address | Rows read `Name — Lead — Stage` and `Name — Opportunity — Stage`. Both are `crm.lead`; `kind_label` is what separates them. |

**The dangerous case is a send that fails after Odoo already has the record.**
Force it on a draft with an empty **To** — if that client sends it anyway,
temporarily make `sendMessage()` `return Promise.reject(new Error("x"))`. Check
**both** paths, create and append. Expect the error to *name what already
landed* (`The email was added to <name>` / `Lead created (#N)`) and to say not
to do it again. If it shows the bare Outlook error instead, the user will press
the button a second time and get a duplicate note or a duplicate lead.

---

## Phase 4 — Confirm the token really landed

In Odoo: **Settings → Users & Companies → Users →** your user **→ API Keys tab**.
There should be a key named `Aktiv for Outlook (dev)`.

Or from the shell:

```bash
cd /home/odoo/workspace/19
./17env/bin/python odoo/odoo-bin shell -c odoo-addin-test.conf -d addin_test
```
```python
env['res.users.apikeys'].search([('scope', '=', 'odoo.plugin.outlook')]).mapped('name')
```

---

## Phase 5 — Licensing (defer until Phase 1–4 are green)

Only worth starting once the Odoo handshake works end to end:

1. Register an Azure AD app; set the Application ID URI to
   `api://localhost:3000/<client-id>` for dev.
2. Put the client id in `<WebApplicationInfo><Id>` and match `<Resource>`.
3. Build `/api/license`: validate the JWT (signature, `aud`, `iss`), key the
   subscription on the `tid` claim.
4. Flip `DEV_SKIP_LICENSE` to `false` in `config.js`.

---

## Failure modes and what they mean

| Symptom | Cause |
|---|---|
| Panel blank, console CORS error | nginx stripping `Access-Control-Allow-Origin`. Re-run the Phase 1.3 preflight curl. |
| `MODULE_MISSING` | `mail_plugin` not installed on that database. |
| Dialog shows ngrok warning page | Free-tier interstitial. Visit the ngrok URL once in the browser and click through. |
| Dialog redirect-loops or lands on http:// | `proxy_mode = False`. Use `odoo-addin-test.conf`. |
| "Access Error: Only Internal Users…" | You logged in as a portal user. `_is_internal()` gate at `authenticate.py:30`. Portal users can never connect. |
| `Invalid code` from access_token | The 3-minute auth code expired. Reconnect and don't dawdle. |
| Button missing from ribbon | Icon URLs 404, or manifest `<Id>` is still the zero GUID. |
| Add-in won't sideload at all | Tenant blocks custom add-ins, or a manifest schema violation. |
| Button on read but **not on compose** | Old manifest still cached. Remove the add-in and add from file again. |
| Compose panel shows `From: undefined <undefined>` | You're running a pre-compose `taskpane.js` against the new manifest. Read mode's plain `item.from` / `item.subject` don't exist in compose. |
| Attachments missing on records made from a draft | Client below Mailbox 1.8, so no `getAttachmentsAsync`. Deliberate: the record is still created, just without the files. |
| `NO_SUBJECT` on a mail that clearly has a subject | Compose subject is read through `getAsync`; a raw `item.subject` read returns the accessor object, which is truthy but never a string. |
