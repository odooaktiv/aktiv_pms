from odoo import fields, models


class OdooDaysParticipant(models.Model):
    """
    Model Odoo Days Participant stores the registration details of a
    person who signs up for the Odoo Days contest through the public
    website form.

    A participant record captures the personal contact information
    (name, email, mobile), the participant type (which drives the
    survey to be answered), the list of chosen objectives, and a
    reference to the generated survey user input that holds the
    participant's answers.
    """

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
