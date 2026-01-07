{
    "name": "Aktiv Customer Portal",
    "category": "Website",
    "author": "Aktiv Software",
    "version": "17.0.1.0.1",
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
