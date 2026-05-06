from odoo import fields, models


class Technology(models.Model):
    _name = "technology"
    _description = "Technology"

    name = fields.Char(string="Name")
