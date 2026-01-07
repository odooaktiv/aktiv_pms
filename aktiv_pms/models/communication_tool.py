# -*- coding: utf-8 -*-

from odoo import fields, models


class CommunicationTool(models.Model):
    _name = "communication.tool"
    _description = "Communication"

    name = fields.Char("Name")
