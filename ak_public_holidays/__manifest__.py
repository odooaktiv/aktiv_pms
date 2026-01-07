# -*- coding: utf-8 -*-

{
    'name': "Public Holidays List",
    'version': '17.0.1.0.0',
    'author': "Aktiv Software",
    'category': 'Human Resources',
    'description': """
        Public Holidays List
    """,
    'depends': ['base','hr'],
    "data": [
        "security/ir.model.access.csv",
        "views/public_holiday_views.xml",
        "views/hr_employee_views.xml",
        "views/hr_employee_public_views.xml",
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    "license": "OPL-1",
}
