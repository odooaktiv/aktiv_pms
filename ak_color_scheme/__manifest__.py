# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software.
# See LICENSE file for full copyright & licensing details.

# Author: Aktiv Software
# mail:   odoo@aktivsoftware.com
# Copyright (C) 2024-Present Aktiv Software PVT. LTD.
# Contributions:
#           Aktiv Software:
#              - Shahil Chauhan
#              - Parth Radadia
#              - Harshil Soni

{
    "name": "Color Scheme",
    "summary": "Color scheme in odoo",
    "description": """
        This module is used to provide customer wih an option to choose their
        color scheme for odoo
    """,
    "website": "http://www.aktivsoftware.com",
    "company": "Aktiv Software",
    "author": "Aktiv Software",
    "version": "17.0.1.0.0",
    "license": "OPL-1",
    "depends": ["base_setup", "web"],
    "data": [
        "security/ir.model.access.csv",
        "data/pallets_data.xml",
        "views/res_config_settings_views.xml",
        "views/webclient_templates.xml",
        "views/color_scheme_pallet.xml",
    ],
    "assets": {
        "web.assets_backend": [
            (
                "after",
                "web/static/src/webclient/**/*",
                "ak_color_scheme/static/src/**/*",
            ),
        ],
    },
    "images": [
        "static/description/banner.jpg",
    ],
    "auto_install": False,
    "application": False,
    "price": 10,
    "currency": "USD",
}
