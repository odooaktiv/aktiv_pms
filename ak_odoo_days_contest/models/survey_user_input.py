# -*- coding: utf-8 -*-

from odoo import fields, models


class SurveyUserInput(models.Model):
    """Inherited: Survey User Input

    Survey User Input extension to link a submitted survey to the
    Odoo Days Participant who answered it.

    This extension adds a reference to the related
    `odoo.days.participant` record and exposes the participant's
    mobile number as a related field so that it can be displayed and
    searched directly on the survey submission.
    """

    _inherit = 'survey.user_input'

    participant_id = fields.Many2one(
        comodel_name="odoo.days.participant",
        string="Odoo Days Participant",
        copy=False,
        readonly=True
    )
    participant_mobile = fields.Char(
        string="Mobile", related="participant_id.mobile"
    )
