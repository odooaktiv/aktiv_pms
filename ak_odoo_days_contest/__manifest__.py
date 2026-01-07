# -*- coding: utf-8 -*-
{
    "name": "Aktiv Odoo Days Contest",
    "summary": """
    Survey for Odoo days""",
    "description": """
    Survey for Odoo days
    """,
    "author": "Aktiv software",
    "website": "https://www.aktivsoftware.com/",
    "category": "Website",
    "version": "17.0.1.0.0",
    "license": "OPL-1",
    "depends": ["survey", "website"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/participant_type_views.xml",
        "views/odoo_days_participant_views.xml",
        "views/odoo_days_objective_views.xml",
        "views/survey_user_input_views.xml",
        "templates/ak_odoo_days_contest_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ak_odoo_days_contest/static/src/scss/portal.scss",
            "ak_odoo_days_contest/static/src/scss/fonts.scss",
            "ak_odoo_days_contest/static/src/js/portal.js",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}
