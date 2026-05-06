# -*- coding: utf-8 -*-

from odoo import models, fields
from datetime import date, datetime


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    holiday_list_id = fields.Many2one('public.holiday', string="Public Holiday List")

    def is_holiday(self, date, holiday_list):
        """Check if a given date is a holiday in the specified holiday list"""
        if not holiday_list or not date:
            return False
        return any(line.date == date for line in holiday_list.line_ids)
