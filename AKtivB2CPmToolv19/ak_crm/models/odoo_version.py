from odoo import fields, models


class OdooVersion(models.Model):
    _name = "odoo.version"
    _description = "OdooVersion"

    name = fields.Char(string="Name")
