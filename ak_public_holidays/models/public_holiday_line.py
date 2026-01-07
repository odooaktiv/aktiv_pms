# -*- coding: utf-8 -*-

from odoo import models, fields


class PublicHolidayLine(models.Model):
    _name = 'public.holiday.line'
    _description = 'Public Holiday Line'

    list_id = fields.Many2one('public.holiday', string="Holiday List", ondelete="cascade", index=True)
    date = fields.Date(string="Date", required=True)
    name = fields.Char(string="Holiday Name", required=True)
