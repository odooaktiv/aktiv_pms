from odoo import fields, models


class ParticipantType(models.Model):
    """
    Model Participant Type defines a category of Odoo Days contest
    participant along with the Survey that such participants are
    required to answer.

    Each record links a human-readable Name to a specific
    `survey.survey`, so that during registration the correct survey
    is assigned to the participant based on the type they select.
    """

    _name = "participant.type"
    _description = "Participant Type"

    name = fields.Char(string="Name", required=True)
    survey_id = fields.Many2one(
        comodel_name="survey.survey", string="Survey", required=True
    )
