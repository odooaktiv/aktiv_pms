# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class AktivMeetings(models.Model):
    _name = "knowledge.bank"
    _description = "Knowledge Bank"

    name = fields.Char(string="Name")
    version_ids = fields.Many2many("odoo.version", string="Version")
    code = fields.Html(string="Code")
    user_ids = fields.Many2many("res.users")
