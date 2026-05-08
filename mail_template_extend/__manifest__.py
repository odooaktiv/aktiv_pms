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
    'name': "Email Template Layout Changes",
    'version': '19.0.1.0.0',
    'summary': 'Mail',
    'description': """
        Used to extend mail and remove footer in email template layout.
        """,
    'depends': ['mail'],
    'data': [
            'data/mail_templates_email_layouts.xml'
        ],
    'author': "Aktiv Software",
    'category': 'Productivity',
    'installable': True,
    'application': False,
    'auto_install': False,
    "license": "OPL-1",
}
