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
    "name": "Aktiv Customer Portal",
    "category": "Website",
    "author": "Aktiv Software",
    "version": "19.0.1.0.0",
    "license": "OPL-1",
    "depends": [
        "project",
        "website",
        "aktiv_pms",
        "hr_timesheet",
        "auth_signup",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/project_portal_templates.xml",
        "views/reset_password_template.xml",
        "views/hr_timesheet_portal_templates.xml",
        "views/webclient_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ak_customer_portal/static/src/scss/portal.scss",
            "ak_customer_portal/static/src/css/portal.css",
            "ak_customer_portal/static/src/scss/ak_customer_portal_login.scss",
            "ak_customer_portal/static/src/css/login.css",
            "ak_customer_portal/static/src/js/task_details_renderer.js",
        ],
    },

    "installable": True,
    "application": False,
    "auto_install": False,
}
