from odoo import fields, models


class OdooDaysParticipant(models.Model):
    _name = "odoo.days.participant"
    _description = "Odoo Days Participant"

    name = fields.Char(string="Name", required=True)
    email = fields.Char(string="Email", required=True)
    mobile = fields.Char(string="Mobile", required=True)
    objectives = fields.Many2many(
        comodel_name="odoo.days.objective", string="Objectives", required=True
    )
    participant_type = fields.Many2one(
        comodel_name="participant.type", string="Type", required=True
    )
    answers = fields.Many2one(
        comodel_name="survey.user_input", string="Answers", readonly=True
    )
