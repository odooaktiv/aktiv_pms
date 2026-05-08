# -*- coding: utf-8 -*-

import base64

from odoo import models


class SurveyWinner(models.TransientModel):
    _name = "survey.winner"
    _description = "Survey Winner"

    def action_print_certificate(self):
        survey_user_input_ids = self.env["survey.user_input"].browse(
            self._context.get("active_ids", False)
        )
        if not survey_user_input_ids:
            return False
        return self.env.ref(
            "ak_survey.contest_certificate_report"
        ).report_action(survey_user_input_ids[0])

    def action_send_survey_winner_email_print(self):
        email_template = self.env.ref(
            "ak_survey.contest_winner_mail_template", raise_if_not_found=False
        )
        survey_user_input_ids = self.env["survey.user_input"].browse(
            self._context.get("active_ids", False)
        )
        if email_template and survey_user_input_ids:
            if survey_user_input_ids:
                generated_report = self.env["ir.actions.report"]._render_qweb_pdf(
                    "ak_survey.contest_certificate_report",
                    res_ids=[survey_user_input_ids[0].id],
                )
                data_record = base64.b64encode(generated_report[0])
                ir_values = {
                    "name": "Contest Certificate",
                    "type": "binary",
                    "datas": data_record,
                    "mimetype": "application/pdf",
                    "res_model": "survey.user_input",
                }
                report_attachment = (
                    self.env["ir.attachment"].sudo().create(ir_values)
                )
                email_template.attachment_ids = [(4, report_attachment.id)]
                email_template.send_mail(
                    survey_user_input_ids[0].id, force_send=True
                )
                survey_user_input_ids[0].is_winner = True
                return self.action_print_certificate()
