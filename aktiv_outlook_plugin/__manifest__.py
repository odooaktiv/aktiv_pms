# -*- coding: utf-8 -*-
{
    "name": "Aktiv Outlook Plugin",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "summary": "Direct username/password login and CRM Lead / Opportunity / Helpdesk Ticket "
                "creation (with attachments) for the Aktiv Outlook add-in.",
    "description": """
Aktiv Outlook Plugin
====================

Two small additions on top of ``mail_plugin``, for the Aktiv Outlook add-in:

* ``/aktiv/auth/login`` - a direct username/password (or API key) login, so the
  add-in can offer a plain login form instead of the OAuth popup/consent
  dialog. On success it mints the same ``odoo.plugin.outlook`` scoped API key
  ``mail_plugin``'s own dialog flow produces, so everything downstream
  (``auth_method_outlook`` in ``mail_plugin/models/ir_http.py``) is unchanged.

* ``/aktiv/lead/create`` and ``/aktiv/helpdesk/create`` - create a CRM Lead or a
  Helpdesk Ticket from the email currently open in Outlook (``lead_type=
  'opportunity'`` on the first creates a CRM Opportunity instead), attaching the
  sender as a partner (found by email, created if missing) and copying over
  any attachments the add-in sends.
""",
    "author": "Aktiv Software",
    "website": "https://www.aktivsoftware.com",
    "license": "LGPL-3",
    "depends": ["mail_plugin", "crm", "helpdesk"],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
