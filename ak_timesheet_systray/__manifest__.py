# -*- coding: utf-8 -*-

{
    "name": "Aktiv Timesheet List",
    "version": "19.0.1.0.0",
    "summary": "Smart view of timesheet entries based on employees",
    "description": """
        This module enables quick access to timesheet entries via a smart dropdown from the timesheet system tray.
        """,
    "author": "Aktiv Software",
    "company": "Aktiv Software",
    "website": "http://www.aktivsoftware.com",
    "category": "Extra Tools",
    "license": "AGPL-3",
    "depends": ['web', 'analytic', 'aktiv_pms'],
    "data": [
    ],
    "assets": {
        "web.assets_backend": [
            # "ak_timesheet_systray/static/src/**/*",
            # 'ak_timesheet_systray/static/scss/timesheet_style.scss'
        ],
    },
    "installable": True,
    "auto_install": False,
}
