# -*- coding: utf-8 -*-

from odoo import fields, models


class MonthDate(models.Model):
    _name = "month.date"
    _description = "Month date"

    name = fields.Char(string="Name")
    value = fields.Integer(string="Value")
