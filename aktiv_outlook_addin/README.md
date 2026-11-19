# Aktiv for Outlook — scaffold

Auth flow and manifest for a commercial Odoo↔Outlook add-in. The plumbing is
complete; the product is not. `renderHook()` in `taskpane.js` is the only
function that depends on the differentiator, and it's stubbed.

## Files

| File | Role |
|---|---|
| `manifest.xml` | AppSource manifest. `AppDomains` = our origin only. `WebApplicationInfo` = the licensing hook. |
| `auth-bounce.html` | Dialog entry point. Exists purely because Office requires the dialog's *initial* URL to be same-domain. |
| `auth-callback.html` | Odoo redirects back here; calls `messageParent` from our origin. |
| `taskpane.html` / `taskpane.js` | The panel: connect form, auth handshake, licence check, hook. |

Everything is served from one origin (`https://addin.example.com` — replace it).
Flat static hosting plus one `/api/license` endpoint.

## Before it runs

1. Generate a real GUID for `<Id>` and never change it — it keys every install.
2. Register an Azure AD app; put its client id in `<WebApplicationInfo><Id>` and
   match `<Resource>` to its Application ID URI.
3. Build `/api/license`: validate the incoming JWT (signature, `aud`, `iss`),
   then key the subscription on the `tid` tenant claim.
4. Icons at 16/32/64/80/128 px.
5. Sideload `manifest.xml` to test before going anywhere near Partner Center.

## Targeting Odoo 19

Every route signature, response shape and error path here was read out of
`/home/odoo/workspace/19/odoo/addons/mail_plugin`, not from docs or memory. Line
references in the comments point into that tree.

If you later support 15→19 in one build, the shapes below are the ones to re-check
per version — `partner/get` in particular has accumulated backwards-compat cruft
(the `id: -1` sentinel exists purely to keep old plugin builds working).

**`partner/get` is not read-only.** On a miss, if the user has create rights, it
calls `_create_company_from_iap()` and will create *and* IAP-enrich a company
(`mail_plugin.py:188`). That spends the customer's IAP credits and writes to their
database — triggered by nothing more than opening an email. Decide deliberately
whether your panel should call it on load or only behind a button; billing
customers for surprise IAP spend is a support ticket you don't want.

## Gotchas that will cost you an afternoon each

**The 3-minute window.** `auth_confirm` mints an HMAC-signed code that
`_get_auth_code_data` rejects after 3 minutes (`authenticate.py:95`). Redeem it
the moment the dialog returns. Don't queue it behind anything.

**JSON-RPC, not JSON.** Odoo `type='json'` routes need the full
`{jsonrpc, method, params, id}` envelope. Post bare JSON and the route sees no
params and fails confusingly. `odooRpc()` handles this.

**Preflight on your own endpoints.** `Authorization` + `application/json`
triggers a CORS preflight. If you set `methods=['POST']` on a route you must
also allow `'OPTIONS'` or preflight 405s — Odoo's own code carries a comment
about exactly this at `authenticate.py:64`. Omitting `methods` entirely is safe.

**Internal users only.** `/mail_plugin/auth` renders an access error for anyone
failing `_is_internal()` (`authenticate.py:30`), and `_generate_auth_code`
raises `NotFound` for them too. Portal users cannot connect this add-in, ever.
That's a pricing constraint, not a bug: your addressable seats are your
customers' *internal* Odoo users. Say so on the listing or you'll eat support
tickets from people trying to connect portal accounts.

**Version spread.** Public means arbitrary customers on 15→19, CE and EE.
`check_version` returns `1` and is your only handshake for "is the module even
there". `helpdesk_mail_plugin` is EE-only — never assume ticket creation exists.

**Don't fork `mail_plugin`.** It's LGPL-3. Inherit and add your own controllers
in your own module and you keep the OPL-1 option; copy its source and your
module becomes a derivative work that must ship as LGPL-3.

## Still open

- The hook. Without it there's nothing to put in the panel that Odoo SA doesn't
  already give away free.
- Trademark clearance for the listing name (see the Odoo partner agreement).
- A permanent public demo Odoo with credentials — AppSource reviewers must be
  able to exercise the full flow, on first submission and every update after.
