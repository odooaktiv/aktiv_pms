# -*- coding: utf-8 -*-

from odoo import fields, models


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    is_winner = fields.Boolean("Is Winner")

    def action_declare_winner(self):
        return {
            "name": "Declare Winner",
            "res_model": "survey.winner",
            "view_mode": "form",
            "context": {
                "active_model": "survey.user_input",
                "active_ids": self.ids,
            },
            "target": "new",
            "type": "ir.actions.act_window",
        }
