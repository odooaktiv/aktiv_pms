from odoo import fields, models


class OdooDaysObjective(models.Model):
    """
    Model Odoo Days Objective defines the list of objectives that a
    participant can choose while registering for the Odoo Days contest.

    Each objective record stores a display Name and a Sequence used to
    control the order in which objectives are presented to participants
    on the public registration form.
    """

    _name = "odoo.days.objective"
    _description = "Odoo Days Objective"
    _order = "sequence"

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="Sequence")
