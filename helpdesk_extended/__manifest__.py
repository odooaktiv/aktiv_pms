# -*- coding: utf-8 -*-

{
    'name': "Helpdesk Email Template Changes",
    'version': '19.0.1.0.0',
    'summary': 'Mail',
    'description': """
        Inherited Helpdesk Closed Email Template
        """,
    'depends': ['mail', 'helpdesk_mgmt'],
    'data': [
            'data/helpdesk_template.xml'
        ],
    'author': "Aktiv Software",
    'category': 'Productivity',
    'installable': True,
    'application': False,
    'auto_install': False,
    "license": "OPL-1",
}
