# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    linkedin_page = fields.Char(string="LinkedIn Page")
    linkedin_profile = fields.Char(string="LinkedIn Profile")
    linkedin_id = fields.Char(string="LinkedIn ID")
    no_of_employees = fields.Char(string="No. of Employees")
