from odoo import fields, models


class ParticipantType(models.Model):
    _name = "participant.type"
    _description = "Participant Type"

    name = fields.Char(string="Name", required=True)
    survey_id = fields.Many2one(
        comodel_name="survey.survey", string="Survey", required=True
    )
