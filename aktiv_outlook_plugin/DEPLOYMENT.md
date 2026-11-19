# Deploying Aktiv for Outlook

Covers a fresh production install and every kind of update afterwards.

The product is two halves that deploy independently:

| Half | What it is | Lives in |
|---|---|---|
| **Odoo module** | `aktiv_outlook_plugin` — the `/aktiv/*` routes | this repo |
| **Add-in** | static files + `manifest.xml` — the panel Outlook loads | `aktiv_outlook_addin/` at the root of this repo |

> **Both halves are in this repo, but only one of them deploys itself.** The
> module is on the addons path and arrives with a checkout. The add-in is
> static files that a web server serves — being in the repo versions them, it
> does not put them on the web root. Deploying the panel is still the copy in
> §4/§7, from `aktiv_outlook_addin/` to the server's web root.
>
> `aktiv_outlook_addin/` has no `__manifest__.py`, so Odoo does not see it as a
> module even though the repo root is on the addons path. Do not add one.

---

## 1. Requirements

- **Odoo 19**, Community or Enterprise
- Modules installed: **`mail_plugin`** (community, free), **`crm`**, **`helpdesk`**
  (Enterprise). These are `aktiv_outlook_plugin`'s declared `depends`.
- **HTTPS with a publicly valid certificate.** Not negotiable: the panel refuses
  anything but `https://` (`normalizeOdooUrl` in `taskpane.js`), and Outlook will
  not load mixed content into an add-in frame. A self-signed cert will fail.
- Somewhere to serve ~8 static files over HTTPS.
- Microsoft 365 tenant admin, to publish the add-in to users.

Users who connect must be **internal** users. Portal and public users are
refused by `/aktiv/auth/login` (`_is_internal()`).

---

## 2. Three decisions before you touch anything

### 2.1 There is no licence enforcement in this build

`config.js` ships `DEV_SKIP_LICENSE: true`, above a comment saying never to ship
that. Ship it anyway — **it has to stay `true`.**

`checkLicense()` short-circuits on that flag. Set it `false` and the panel calls
`Office.auth.getAccessTokenAsync()`, which needs an Azure AD app registration
wired into `<WebApplicationInfo>` in the manifest, and then POSTs to
`ADDIN_ORIGIN/api/license`. Neither exists:

- `<WebApplicationInfo>` is commented out of `manifest.xml`
- `/api/license` was never built (see `README.md`, "Before it runs", step 3)

So with `false` the panel fails on load for every user, and with `true` there is
no subscription check at all. Tell the client which of those they are getting.
Building it means: register an Azure AD app, restore `<WebApplicationInfo>` with
its client id, and implement `/api/license` to validate the JWT (signature,
`aud`, `iss`) and key the subscription on the `tid` tenant claim.

### 2.2 Generate a new `<Id>` GUID

`manifest.xml` carries `f4fca388-c0ec-4cfb-b111-fd8f5d9b597e`. That GUID is the
identity of *this* add-in to Outlook. A tenant cannot hold two add-ins with the
same GUID, so if anyone might also sideload the staging build, the production
manifest needs its own.

Generate once (`uuidgen`), then **never change it** — changing it later orphans
every existing install, and users must remove and re-add the add-in.

### 2.3 Serve the add-in from the same origin as Odoo

Staging serves the panel at `https://odoo.aktivsoftware.com/addin` — the same origin
as the Odoo it talks to. Copy that. When the panel and Odoo share an origin, the
`/aktiv/*` calls are **same-origin requests and CORS never applies**.

Split them across two domains and every request depends on CORS headers being
right on both the success *and* the failure path — which is exactly the class of
bug documented in section 7.2. It works, but it is strictly more to get wrong.

---

## 3. Part A — the Odoo module

```bash
# 1. Put the module in the addons_path (however you deploy custom modules:
#    git checkout, rsync, image build). It must land beside your other
#    custom modules, in a directory named exactly aktiv_outlook_plugin.

# 2. Install it.
odoo-bin -c /etc/odoo.conf -d <database> -i aktiv_outlook_plugin --stop-after-init

# 3. Restart.
systemctl restart <your-odoo-service>
```

Confirm all four modules are installed:

```sql
SELECT name, state FROM ir_module_module
 WHERE name IN ('mail_plugin','aktiv_outlook_plugin','crm','helpdesk');
```

All four must read `installed`. `mail_plugin` is not installed by default on a
stock database — it is the one most often missing.

> If the server has more than one Odoo config file, confirm which one the running
> process actually uses (`ps aux | grep odoo-bin`) before trusting its `db_name`.
> A stale config in `/etc/` naming a different database will send you chasing
> module states on a database nobody is serving.

---

## 4. Part B — the static add-in files

Copy these to the web root — the whole set, nothing else:

```
assets/            (icon-16, icon-32, icon-64, icon-80, icon-128 .png)
auth-bounce.html
auth-callback.html
config.js
manifest.xml
support.html
taskpane.html
taskpane.js
```

Then edit **`config.js`**:

```js
window.AKTIV_CONFIG = {
  ADDIN_ORIGIN: "https://odoo.client.com/addin",  // must match where these files are served
  FRIENDLY_NAME: "Aktiv for Outlook",               // drop the "(dev)"
  SCOPE: "outlook",                               // leave alone — Odoo prefixes it
  DEV_SKIP_LICENSE: true,                         // must stay true, see 2.1
};
```

### Web server

Serve the directory under `/addin` on the Odoo vhost, ahead of the Odoo
`proxy_pass`, and send **`Cache-Control: no-store`**. That header is what makes
JS updates reach users without anyone clearing a cache — it is already how
staging is configured, and it is why a static-file update needs no user action.

This is the block running on production (`odoo.aktivsoftware.com`, in
`/etc/nginx/sites-available/aktivsoftware.com.conf`, inside the `listen 443 ssl` server
for that hostname and above its `location /`). Adapt the alias path; keep
everything else.

```nginx
location ^~ /addin/ {
    alias /opt/odoo/19.0/custom_addons/aktiv_outlook_addin/;
    include /etc/nginx/mime.types;
    add_header Cache-Control "no-store" always;
}
```

Three things that are not obvious, each of which produced a working-looking
deployment that was in fact broken:

* **`^~`, not a plain prefix.** The Odoo vhosts carry regex locations for
  static extensions, and a regex location beats a plain prefix location.
  Without `^~` the HTML and XML served fine while every `.js` and `.png` went
  to Odoo and 404'd - so the panel loaded and then died fetching `config.js`,
  which reads as "the add-in is broken" rather than "nginx is misrouting".

* **`include mime.types`.** Without it every file is served as
  `application/octet-stream`, and Outlook's webview will not execute a script
  with that type. The panel opens blank and the console error names the script,
  not the header. Verify the type, not just the status code.

* **Traverse permission on the whole path.** The files are readable, but nginx
  also has to reach them. `/odoo` ships `drwxr-x---`, which stops `www-data`
  dead and answers **403**, not 404 - and nothing is written to the nginx error
  log, because the traverse fails before any file is opened. `chmod o+x /odoo`
  is enough; `o+x` allows traversal without allowing the directory to be
  listed. Diagnose with `namei -l <full path to taskpane.html>`.

Check it - status, type and cache header, for a JS file and an HTML one:

```bash
for f in taskpane.html taskpane.js config.js manifest.xml; do
    curl -sI https://odoo.client.com/addin/$f | head -1
    curl -sI https://odoo.client.com/addin/$f | grep -i -e content-type -e cache-control
done
# expect: 200, text/html + application/javascript + text/xml, Cache-Control: no-store
```

> **`/addin` is served straight out of the git checkout.** A later `git pull`
> on that clone reverts `config.js` and `manifest.xml` to the staging values
> committed in the repo, and the add-in breaks for every user with no
> deployment having taken place. Either copy the directory somewhere outside
> the checkout and alias that, or re-apply the host rewrite as a deploy step.

---

## 5. Part C — the manifest

`manifest.xml` hardcodes the staging host in **11 lines** — 10 live, plus one
inside the commented-out Azure block:

| Line | Element |
|---|---|
| 18 | `IconUrl` |
| 19 | `HighResolutionIconUrl` |
| 20 | `SupportUrl` |
| 26 | `AppDomain` |
| 42, 51 | `SourceLocation` (read and compose) |
| 136–138 | `bt:Image` icon16 / icon32 / icon80 |
| 141 | `bt:Url` taskpaneUrl |
| 170 | `Resource` (inside the commented `<WebApplicationInfo>`) |

Replace them all at once rather than by hand:

```bash
sed -i 's#https://odoo\.aktivsoftware\.com#https://odoo.client.com#g; s#api://odoo\.aktivsoftware\.com#api://odoo.client.com#g' manifest.xml

grep -c "odoo.aktivsoftware.com" manifest.xml   # must print 0
```

Then set the new GUID (section 2.2) and the version:

```xml
<Id>YOUR-NEW-GUID-HERE</Id>
<Version>1.0.0.0</Version>
```

`<Version>` must **increase on every manifest change** or Outlook keeps serving
the cached one.

### Publishing to Outlook

**Tenant-wide:** Microsoft 365 admin center → **Settings → Integrated apps →
Upload custom apps** → upload `manifest.xml` → assign users. Rollout takes up to
24 hours.

**Single mailbox, for testing:** Outlook → **Get Add-ins → My add-ins → Add a
custom add-in → Add from file**. Immediate.

---

## 6. Part D — verify before handing over

```bash
ODOO=https://odoo.client.com

# Routes registered and CORS-clean. Expect {"result":{"error":"TOKEN_REJECTED"}}
for p in /aktiv/lead/create /aktiv/helpdesk/create /aktiv/record/search /aktiv/record/append; do
  printf '%-24s ' "$p"
  curl -s -X POST -H 'Content-Type: application/json' \
       -H 'Authorization: Bearer definitely-invalid' \
       -H "Origin: $ODOO" \
       -d '{"jsonrpc":"2.0","method":"call","params":{"kind":"lead","id":1,"subject":"x"},"id":null}' \
       "$ODOO$p"; echo
done

# Login route. Expect {"result":{"error":"Invalid username or password."}}
curl -s -X POST -H 'Content-Type: application/json' \
     -d '{"jsonrpc":"2.0","method":"call","params":{"login":"nobody@x.test","password":"wrong"},"id":null}' \
     "$ODOO/aktiv/auth/login"; echo

# CORS preflight. Expect 204 + Access-Control-Allow-Origin
curl -s -o /dev/null -D - -X OPTIONS \
     -H "Origin: $ODOO" -H 'Access-Control-Request-Method: POST' \
     -H 'Access-Control-Request-Headers: content-type,authorization' \
     "$ODOO/aktiv/lead/create" | grep -iE '^HTTP/|access-control'
```

**An HTML page instead of JSON means 404** — the module is not installed, or
Odoo was not restarted after the files changed.

Then in Outlook: open a mail → connect → **Create CRM Lead** → **Add to existing
Lead…** on the same sender. The chatter note should render the email, not show
its HTML source.

Then start a **New email** to that same address and use **Send & add to Lead…**
(see 7.3). The mail should land in **Sent Items** and the record should carry
one new note headed `Sent to: …`. If that row isn't on the panel, the client is
below Mailbox 1.15 — expected on Mac, LTSC and on-premises Exchange, not a
deployment fault.

---

## 7. Updating an existing installation

Most updates need **no manifest change and no action from users.**

| What changed | Steps | Users must |
|---|---|---|
| `hooks.py`, `auth.py` — Python only | copy file → **restart Odoo** | nothing |
| New models / XML / data files | copy → `-u aktiv_outlook_plugin` → restart | nothing |
| `taskpane.js`, `taskpane.html`, `config.js` | copy the file, and change the `?v=` on the script tags in `taskpane.html` (release date). No restart | reopen the panel |
| `manifest.xml` | **bump `<Version>`** → re-upload in Integrated apps | wait up to 24h |

The **send-and-file** feature (§7.3) is the first two rows only — `hooks.py` plus
`taskpane.js`/`taskpane.html`. It needs no manifest change, so no re-upload and
no 24-hour wait.

### 7.1 The restart is the trap

Odoo builds its routing map at startup. A changed `hooks.py` sitting in the
addons path does **nothing** until the process re-imports it — the routes keep
returning 404 while the correct code is on disk a metre away. Any Python change
needs a restart. No `-u` is required for a controller-only change, because this
module ships no data files.

### 7.2 Do not "fix" `auth='none'` on the routes

The routes in `hooks.py` are declared `auth='none'` and call
`_authenticate_outlook()` as the **first statement** of every handler. This looks
wrong and is deliberate. Do not change it back to `auth='outlook'`.

Odoo attaches CORS headers in `Dispatcher.pre_dispatch`, but `_serve_ir_http`
calls `_authenticate()` *before* `_pre_dispatch()`. So an `auth='outlook'`
rejection produces an error response with no `Access-Control-Allow-Origin` — and
a cross-origin reply missing that header is one the browser discards without
handing it to the page. The panel's `fetch()` then fails identically to the
server being down, and an expired token reports itself as *"couldn't reach that
Odoo server, check the URL and CORS"*, which sends people auditing healthy
infrastructure for hours.

Authenticating inside the handler keeps the reply on the normal dispatch path,
headers and all, so the panel can read it and say "reconnect". The credential
check itself is unchanged — it delegates to `mail_plugin`'s own
`_auth_method_outlook`, including its `request.update_env(user=...)`, so handler
code still runs as the API key's user.

If you add a route, copy the pattern: `auth='none'`, `cors='*'`, and
`_authenticate_outlook()` first.

### 7.3 Send-and-file, and why it is not in the manifest

Four buttons, mirroring the two rows above them — create something new, or file
onto something that exists — except these also send the draft, in one click,
instead of filing and then going to press Send:

```
Send & create Lead       Send & create Ticket
Send & add to Lead…      Send & add to Ticket…
```

`Send & add to…` needs a record to file onto, so for a customer with nothing in
Odoo yet the picker says "No leads found" — and offers **Create a new lead and
send** there, carrying the send choice across, rather than ending the flow.

The send half is `item.sendAsync`, from **Mailbox requirement set 1.15**. That
is newer than most of what this add-in uses, and the clients split:

| Client | Has it? |
|---|---|
| Outlook on the web (modern, Exchange Online) | yes |
| new Outlook for Windows | yes |
| classic Outlook for Windows | from **Version 2412 (Build 18324.20172)** |
| Outlook for Mac | **no** — tops out at 1.14 |
| LTSC 2024 / LTSC 2021 | **no** — 1.14 / 1.9 |
| Any client against **on-premises Exchange** | **no** — Exchange on-prem caps every client at 1.5 |

So it is **feature-detected at runtime** (`canSendFromPanel()` in `taskpane.js`),
not declared in the manifest. Where `sendAsync` is missing, the row is replaced
by a line naming the clients that have it, and **Add to existing…** still works
as before.

**Do not "fix" this by raising `MinVersion` to 1.15.** The declared requirement
set does not gate which APIs the code may call — it only gates which clients
will load the add-in at all. Raising it would remove the whole add-in from Mac,
LTSC and every on-premises deployment in order to hide one button. The Office
docs are explicit: "Setting a requirement set doesn't limit the available APIs
that the add-in can use."

This also means the feature ships as a **static-file update** — copy `hooks.py`
(restart Odoo) and `taskpane.js` / `taskpane.html`. No new GUID, no `<Version>`
bump, no re-upload, no 24-hour rollout, nothing for users beyond reopening the
panel.

**Odoo happens before sending, deliberately** — in both the create and the
append path. Odoo is the half that can fail recoverably; if it refuses, the
draft is untouched and can be retried. Sending first would mean a failure
leaves a mail already gone to the customer with nothing in Odoo — the exact gap
the feature closes. The one case that needs care is a send that fails *after*
the record landed: the panel names what it already created or filed to and
tells the user not to do it again, because the obvious reflex — fix the draft,
click the button again — makes a second note or a second lead. Both paths share
one helper (`showSendFailedAfter`) so that wording cannot drift apart.

---

## 8. Troubleshooting by panel message

| Message | Cause | Fix |
|---|---|---|
| *Connect your Odoo server to continue.* | No stored token | Connect |
| *That Odoo server doesn't recognise this request…* | HTTP 404 on the route: module missing, **or Odoo not restarted after an update** | §3, §7.1. The message names the URL it tried |
| *Your Odoo access has expired or was revoked.* | API key deleted or invalid | Reconnect. Check **Settings → Users → API Keys** |
| *Couldn't reach that Odoo server…* | `fetch` never got a reply: wrong URL, DNS, TLS, or blocked CORS | **Read the "Tried:" line in the message** — it names the exact origin dialled, which is usually the whole answer |
| *Only internal users can connect this add-in.* | Portal/public user | Use an internal user |
| *Wrong database name for this server.* | Database field does not match | Clear it, or enter the right name |
| *Odoo URL must use https://* | `http://` entered | HTTPS only |
| *Sending from this panel needs Outlook on the web…* | Client below Mailbox 1.15 | Expected on Mac, LTSC and on-prem Exchange. §7.3 — not a deployment fault |
| *The email was added to X, but Outlook wouldn't send it* | Filing succeeded, `sendAsync` failed | The note **is** on the record. Press Send in Outlook; do not click the button again or you get a second copy |

**The panel header shows the connected server and user.** Before debugging
anything network-shaped, read it. A stale URL left over from an earlier connect
— a dead tunnel, a decommissioned host — is by far the most common cause of
*"couldn't reach that Odoo server"*, and the header answers it instantly.

To move a mailbox to a different server: **Disconnect**, then type the new URL.
The field is pre-filled with the old one to type over.

---

## 9. Disclose to the client's security review

- **An Odoo API key is stored in Outlook's roaming mailbox settings.** It is a
  long-lived credential living in the user's mailbox, syncing across their
  Outlook clients. Recommend users paste a **dedicated API key** into the
  password field rather than their account password — the field accepts either,
  and a scoped key can be revoked without a password reset.
- **API keys expire** after `mail_plugin.access_token_expiration_days` days (default 30, Odoo 19 behaviour); users then reconnect. Users with 2FA must paste an API key, not their password.
- **The password is never stored.** `/aktiv/auth/login` exchanges it once for a
  scoped key (`odoo.plugin.outlook`, labelled "Aktiv for Outlook") and keeps only
  that.
- **No licence enforcement** in this build — see 2.1.
- **Email bodies are sent to Odoo** and stored on the record, including
  attachments. Data path is the customer's Outlook to the customer's own Odoo;
  the add-in origin serves static files only and is never in the data path.
- Chatter notes post as `mail.mt_note` (internal note), so filing an email onto
  a record does **not** email it out to that record's followers.

---

## 10. Known gaps

- `/api/license` unimplemented; `DEV_SKIP_LICENSE` load-bearing (2.1).
- `<WebApplicationInfo>` / Azure AD not registered (2.1).
- Inline images (`<img src="cid:…">`) are stripped from chatter notes. Office.js
  exposes no content-id on `AttachmentDetails`, so there is nothing to repoint
  them at, and leaving them in renders broken-image icons. Normal file
  attachments are uploaded and linked to the note.
- `manifest.xml` requests Mailbox 1.3. On clients below Mailbox 1.8, records
  created from a *compose* draft are created without attachments rather than
  failing.
- **Send-and-file needs Mailbox 1.15**, so it is absent on Outlook for Mac, on
  the LTSC builds, and on any client talking to on-premises Exchange (see 7.3).
  Those users file and press Send as two steps, as before. Covering them would
  mean the `OnMessageSend` (Smart Alerts, 1.12) route instead — filing on the
  way out of Outlook's own Send button. That reaches Mac and classic Outlook
  2206+, but it needs an event runtime (`commands.html` + a standalone
  `launchevent.js`), a manifest re-upload, and `VersionOverrides` raised to
  1.12 — which **removes the ribbon button from on-premises Exchange
  entirely**, since on-prem caps at 1.5. Worth doing only if the client has Mac
  or on-prem users who need it; it is not a free upgrade.
- The `OnMessageSend` route also has a five-second budget before Outlook shows
  "this add-in is taking longer than expected", which uploading a large
  attachment to Odoo will exceed. The panel route has no such limit — another
  reason it is the default.
- The add-in's web root is not deployed by a checkout — the panel files still
  have to be copied to the server by hand (§4, §7). Serving them from the Odoo
  module's own `static/` directory would remove that step and put the panel on
  the same origin as Odoo, which §2.3 already recommends; it costs a manifest
  URL change and therefore a re-upload, so it is a deliberate change, not a
  tidy-up.
