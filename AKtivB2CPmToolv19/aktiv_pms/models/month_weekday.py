# -*- coding: utf-8 -*-

from odoo import fields, models


class MonthWeekday(models.Model):
    _name = "month.weekday"
    _description = "Month Weekday"

    name = fields.Char(string="Name")
    value = fields.Integer(string="Value")
