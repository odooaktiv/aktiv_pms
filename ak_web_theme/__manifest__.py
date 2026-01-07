{
    "name": "AIC Web Theme",
    "summary": "Add Enterprise Web Theme",
    "description": """
        This module adds enterprise web theme to PMS
    """,
    "version": "17.0.1.0.0",
    "category": "Extra Tools",
    "license": "LGPL-3",
    "author": "Aktiv Software",
    "website": "http://www.aktivsoftware.com",
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
