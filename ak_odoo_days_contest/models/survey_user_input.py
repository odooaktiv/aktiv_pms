# -*- coding: utf-8 -*-

from odoo import fields, models


class SurveyUserInput(models.Model):
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
