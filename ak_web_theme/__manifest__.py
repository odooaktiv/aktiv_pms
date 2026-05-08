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
    "name": "Web Theme",
    "summary": "Add Enterprise Web Theme",
    "description": """
        This module adds enterprise web theme to PMS
    """,
    "version": "19.0.1.0.0",
    "category": "Extra Tools",
    "license": "OPL-1",
    "author": "Aktiv Software",
    "website": "https://aktivsoftware.com",
    "depends": ["muk_web_theme", "ak_color_scheme"],
    "excludes": [
        "web_enterprise",
    ],
    "data": ["views/webclient_templates.xml"],
    "assets": {
        "web.assets_backend": [
            "ak_web_theme/static/src/*/**",
        ],
        "web._assets_primary_variables": [
            "ak_web_theme/static/src/scss/variables.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
