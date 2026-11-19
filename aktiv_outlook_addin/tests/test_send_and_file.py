#!/usr/bin/env python3
"""Backend test for the send-and-file change in aktiv_outlook_plugin.

Exercises the two routes the add-in's new button calls, the way the add-in
calls them (JSON-RPC + Bearer API key), and asserts on what actually lands in
the chatter - which is the part that was wrong before.

    python3 test_send_and_file.py [--url http://localhost:8019] [--db aktiv_addin_test]

Needs the server running with aktiv_outlook_plugin installed. Seeds its own
partner/lead/opportunity/ticket, so an empty database is fine.
"""
import argparse
import os
import sys
import xmlrpc.client
from urllib.request import Request, urlopen
import json

p = argparse.ArgumentParser()
p.add_argument("--url", default="http://localhost:8019")
p.add_argument("--db", default="aktiv_addin_test")
# From the environment, not defaulted to admin/admin: this mints a real API key
# against a real user, and a script that quietly works with the default password
# is a script that encourages leaving it in place.
p.add_argument("--login", default=os.environ.get("Aktiv_LOGIN"))
p.add_argument("--password", default=os.environ.get("Aktiv_PASSWORD"))
A = p.parse_args()

if not A.login or not A.password:
    raise SystemExit(
        "Set Aktiv_LOGIN and Aktiv_PASSWORD (an internal Odoo user on that database), "
        "or pass --login/--password.")

CONTACT_EMAIL = "sarah.miller@northwind-eng.test"
CONTACT_NAME = "Sarah Miller"

failures = []


def check(label, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + label + (f"\n          {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


def rpc(path, params, token=None):
    """Call an Odoo type='json' route exactly as taskpane.js does."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps({"jsonrpc": "2.0", "method": "call", "params": params, "id": None})
    req = Request(A.url + path, data=body.encode(), headers=headers, method="POST")
    payload = json.loads(urlopen(req, timeout=60).read())
    if payload.get("error"):
        raise SystemExit(f"{path} returned a server error:\n"
                         f"{json.dumps(payload['error'], indent=2)[:2000]}")
    return payload["result"]


# ---------------------------------------------------------------- seed data
common = xmlrpc.client.ServerProxy(f"{A.url}/xmlrpc/2/common")
uid = common.authenticate(A.db, A.login, A.password, {})
if not uid:
    raise SystemExit(f"Could not log in to {A.db} as {A.login}. Wrong db or password?")
models = xmlrpc.client.ServerProxy(f"{A.url}/xmlrpc/2/object")


def call(model, method, *args, **kw):
    return models.execute_kw(A.db, uid, A.password, model, method, list(args), kw)


print("\nSeeding…")
partner = call("res.partner", "search", [("email", "=", CONTACT_EMAIL)], limit=1)
partner = partner[0] if partner else call("res.partner", "create", {"name": CONTACT_NAME, "email": CONTACT_EMAIL})

lead_id = call("crm.lead", "create", {
    "name": "Northwind - initial enquiry", "type": "lead",
    "partner_id": partner, "email_from": CONTACT_EMAIL})
opp_id = call("crm.lead", "create", {
    "name": "Northwind - 40 unit rollout", "type": "opportunity",
    "partner_id": partner, "email_from": CONTACT_EMAIL})
ticket_id = call("helpdesk.ticket", "create", {
    "name": "Northwind - login problem",
    "partner_id": partner, "partner_email": CONTACT_EMAIL})
print(f"  lead #{lead_id}  opportunity #{opp_id}  ticket #{ticket_id}")

# --------------------------------------------------------------- auth route
print("\nMinting an add-in API key via /aktiv/auth/login…")
res = rpc("/aktiv/auth/login", {"login": A.login, "password": A.password, "db": A.db})
if res.get("error"):
    raise SystemExit("login route refused: " + res["error"])
token = res["access_token"]
print("  got a token")


def last_note(model, res_id):
    ids = call("mail.message", "search",
               [("model", "=", model), ("res_id", "=", res_id)], limit=1, order="id desc")
    if not ids:
        return {}
    return call("mail.message", "read", ids, fields=["body", "subject", "attachment_ids"])[0]


# ================================================================== the tests
print("\n--- /aktiv/record/search : lead and opportunity must be distinguishable ---")
found = rpc("/aktiv/record/search", {"kind": "lead", "email": CONTACT_EMAIL}, token)
records = {r["id"]: r for r in found.get("records", [])}
check("both crm.lead records come back", lead_id in records and opp_id in records,
      f"got ids {list(records)}")
if lead_id in records and opp_id in records:
    check("the lead is labelled 'Lead'", records[lead_id].get("kind_label") == "Lead",
          f"kind_label={records[lead_id].get('kind_label')!r}")
    check("the opportunity is labelled 'Opportunity'",
          records[opp_id].get("kind_label") == "Opportunity",
          f"kind_label={records[opp_id].get('kind_label')!r}")

tickets = rpc("/aktiv/record/search", {"kind": "ticket", "email": CONTACT_EMAIL}, token)
trec = {r["id"]: r for r in tickets.get("records", [])}
check("the ticket comes back", ticket_id in trec, f"got ids {list(trec)}")
check("helpdesk carries no kind_label (nothing to disambiguate)",
      trec.get(ticket_id, {}).get("kind_label", "") == "",
      f"kind_label={trec.get(ticket_id, {}).get('kind_label')!r}")

print("\n--- /aktiv/record/append : outgoing mail must not read 'From: <customer>' ---")
BODY = '<p>Attached is the quote you asked for.</p><img src="cid:sig01">'
rpc("/aktiv/record/append", {
    "kind": "lead", "id": opp_id, "subject": "Your quote",
    "email": CONTACT_EMAIL, "name": CONTACT_NAME, "body": BODY,
    "direction": "outgoing",
    "attachments": [{"name": "quote.pdf", "content": "JVBERi0xLjQK"}],
}, token)
note = last_note("crm.lead", opp_id)
check("outgoing note reads 'Sent to:'", "Sent to: Sarah Miller" in note.get("body", ""),
      note.get("body", "")[:300])
check("outgoing note does NOT read 'From:'", "From: Sarah Miller" not in note.get("body", ""),
      note.get("body", "")[:300])
check("inline cid: image was stripped", "cid:" not in note.get("body", ""))
check("the real attachment is on the note", len(note.get("attachment_ids") or []) == 1,
      f"attachment_ids={note.get('attachment_ids')}")

print("\n--- backward compatibility : an older panel sends no direction ---")
rpc("/aktiv/record/append", {
    "kind": "lead", "id": lead_id, "subject": "Re: enquiry",
    "email": CONTACT_EMAIL, "name": CONTACT_NAME, "body": "<p>Thanks for getting in touch.</p>",
}, token)
note = last_note("crm.lead", lead_id)
check("omitting direction still reads 'From:' (unchanged behaviour)",
      "From: Sarah Miller" in note.get("body", ""), note.get("body", "")[:300])

print("\n--- ticket append still works, and honours direction ---")
rpc("/aktiv/record/append", {
    "kind": "ticket", "id": ticket_id, "subject": "Re: login problem",
    "email": CONTACT_EMAIL, "name": CONTACT_NAME, "body": "<p>Try this.</p>",
    "direction": "outgoing",
}, token)
note = last_note("helpdesk.ticket", ticket_id)
check("ticket outgoing note reads 'Sent to:'", "Sent to: Sarah Miller" in note.get("body", ""),
      note.get("body", "")[:300])

print("\n--- the note must stay an internal note, not mail the followers ---")
ids = call("mail.message", "search",
           [("model", "=", "crm.lead"), ("res_id", "=", opp_id)], limit=1, order="id desc")
msg = call("mail.message", "read", ids, fields=["subtype_id", "message_type"])[0]
check("posted as mail.mt_note", "Note" in (msg["subtype_id"][1] if msg["subtype_id"] else ""),
      f"subtype={msg['subtype_id']}")

print("\n--- a stale record id must be refused, not traceback ---")
gone = rpc("/aktiv/record/append", {"kind": "lead", "id": 99999999, "subject": "x"}, token)
check("missing record returns a clean error", gone.get("error") == "That record no longer exists.",
      repr(gone))

print("\n--- a bad token must be refused ---")
bad = rpc("/aktiv/record/search", {"kind": "lead", "email": CONTACT_EMAIL}, "definitely-invalid")
check("bad token returns TOKEN_REJECTED", bad.get("error") == "TOKEN_REJECTED", repr(bad))

print("\n" + "=" * 60)
if failures:
    print(f"{len(failures)} FAILED:")
    for f in failures:
        print("  - " + f)
    sys.exit(1)
print("All backend checks passed.")
print(f"\nLook at it in the UI:  {A.url}/odoo/crm/{opp_id}")
