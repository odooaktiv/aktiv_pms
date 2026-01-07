from odoo import fields, models


class OdooDaysObjective(models.Model):
    _name = "odoo.days.objective"
    _description = "Odoo Days Objective"
    _order = "sequence"

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="Sequence")
