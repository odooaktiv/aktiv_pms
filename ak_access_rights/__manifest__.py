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
    "name": "Aktiv Access Rights",
    "description": "",
    "category": "Project",
    "author": "Aktiv Software",
    "version": "19.0.1.0.0",
    "license": "OPL-1",
    "depends": [
        "crm",
        "mail"
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/outgoing_security.xml",
        "views/outgoing_mail.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
