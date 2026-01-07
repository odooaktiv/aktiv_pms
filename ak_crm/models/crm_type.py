# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CrmType(models.Model):
    _name = "crm.type"
    _description = "CRM TYpe"

    name = fields.Char(string="Type")
    key = fields.Char(string="Key")
