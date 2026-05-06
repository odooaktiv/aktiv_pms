# -*- coding: utf-8 -*-

from markupsafe import Markup
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ProjectTaskCheckWizardLines(models.TransientModel):
    _name = "quality.check.points.wizard.lines"
    _description = "Project Task Quality Check Wizard"

    quality_id = fields.Many2one("quality.check.points.wizard", "Quality")
    name = fields.Char("Name")
    is_required = fields.Boolean("Required to Confirm Task")
    is_done = fields.Boolean("Checked ?")


class ProjectTaskCheckWizard(models.TransientModel):
    _name = "quality.check.points.wizard"
    _description = "Project Task Quality Check Wizard"

    quality_check_ids = fields.One2many(
        "quality.check.points.wizard.lines", "quality_id", "Quality Checks"
    )

    def action_confirm_qc(self):
        """Button action to change stage"""
        message = ""
        task_id = self.env["project.task"].search(
            [("id", "=", self._context.get("active_id"))]
        )
        for qc in self.quality_check_ids:
            if qc.is_required and not qc.is_done:
                raise ValidationError(
                    _(
                        "In Order to Change the Stage,"
                        "Please Check Pass all the Code Quality Checks."
                    )
                )
            else:
                task_id.sudo().write(
                    {
                        "state": "cd_review",
                        "code_reviewer_ids": [
                            (4, cd_id)
                            for cd_id in task_id.project_id.code_reviewer_ids.ids[:1]
                        ],
                    }
                )
                message += (
                    "Quality check - %s<br/>Required - %s<br/>Checked -%s<hr>"
                    % (qc.name, qc.is_required, qc.is_done)
                )
                qc.is_done = False
        task_id.message_post(body=Markup(message))
