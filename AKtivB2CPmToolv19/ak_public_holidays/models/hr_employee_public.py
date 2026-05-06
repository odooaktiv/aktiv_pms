# -*- coding: utf-8 -*-

from odoo import models, fields


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    holiday_list_id = fields.Many2one('public.holiday', string="Public Holiday List")
