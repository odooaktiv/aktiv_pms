# -*- coding: utf-8 -*-
{
    "name": "Aktiv Survey",
    "version": "19.0.1.0.0",
    "summary": "Survey modifications",
    "description": """""",
    "author": "Aktiv Software",
    "company": "Aktiv Software",
    "website": "http://www.aktivsoftware.com",
    "category": "EXtra Tools",
    "license": "AGPL-3",
    "depends": ["ak_odoo_days_contest"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template.xml",
        "data/report_paperformat.xml",
        "views/survey_templates.xml",
        "views/survey_user_views.xml",
        "views/contest_certificate_report_template.xml",
        "views/contest_certificate_report.xml",
        "wizard/survey_winner_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ak_survey/static/src/scss/survey.scss",

        ],
        "web.report_assets_common": ["ak_survey/static/src/scss/report.scss"]
    },
    "installable": True,
    "auto_install": False,
}
