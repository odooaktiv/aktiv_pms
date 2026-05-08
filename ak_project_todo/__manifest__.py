# -*- coding: utf-8 -*-
# Part of Odoo, AIC, Aktiv Software
# See LICENSE file for full copyright & licensing details.

# Author: Aktiv Software.
# mail: sales@aktivsoftware.com
# Copyright (C) 2015-Present Aktiv Software PVT. LTD.
# Contributions:
# Aktiv Software:
#    - Shivani Shah
#    - Yash Vandra
#

{
    "name": "Aktiv Project To-do",
    "version": "19.0.1.0.0",
    "summary": "Manage SOP, User Manuals and Documents at one place",
    "description": """
       Manage SOP, User Manuals and Documents at one place
    """,
    "category": "Productivity/To-Do",
    "author": "Aktiv Software",
    "website": "https://www.aktivsoftware.com/",
    "maintainer": "Aktiv software",
    "depends": ["project_todo"],
    "data": [
        "data/project_data.xml",
        "security/project_task_security.xml",
        "security/ir.model.access.csv",
        "views/project_task_views.xml",
        "views/project_todo_views.xml",
        "wizard/mail_wizard_invite_views.xml",
        "wizard/sop_assignment_views.xml",
    ],
    "demo": [],
    # Odoo Store Specific
    "images": ["static/description/icon.png"],
    # Technical
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "OPL-1",
}
