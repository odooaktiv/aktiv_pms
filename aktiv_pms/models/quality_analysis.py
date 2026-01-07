# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, fields, models


class QualityAnalysis(models.Model):
    _name = "quality.analysis"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Quality Analysis Cases"

    sequence = fields.Char(string="Sequence", default="New", readonly=True, copy=False)
    name = fields.Text(string="Description", required=True)
    display_type = fields.Selection(
        [("line_section", "Section")],
        default=False,
        help="Technical field for UX purpose.",
    )
    date = fields.Datetime(string="Test Date", default=datetime.today())
    pre_conditions = fields.Text(
        string="Pre- Condition",
    )
    steps_performed = fields.Text(string="Steps to Perform")
    server = fields.Selection(
        [("staging", "Staging"), ("local", "Local"), ("production", "Production")],
        "Server",
        default="staging",
        tracking=True,
    )
    expected_result = fields.Text(string="Expected Result")
    attachment = fields.Text(string="Actual Result")
    outcomes = fields.Selection(
        [("bug", "Bug"), ("expected", "Expected Result"), ("suggestion", "Suggestion")],
        "Outcomes",
        tracking=True,
    )
    task_id = fields.Many2one("project.task", string="Task", index=True)
    is_updated = fields.Boolean(string="From Redevelopment?", default=False, store=True)
    is_new = fields.Boolean(default=False)
    project_id = fields.Many2one(
        related="task_id.project_id", string="Project", store=True
    )

    def copy_test_case(self):
        copy_line_rec = self.env["quality.analysis"].browse(self._origin.id)
        copy_line_rec.copy(
            {
                "name": copy_line_rec.name,
                "date": datetime.now(),
                "server": copy_line_rec.server,
                "attachment": copy_line_rec.attachment,
                "is_updated": False,
            }
        )

    @api.model
    def create(self, vals):
        """To generate the sequence for the test cases."""

        qa_ids = False
        project_task = False
        if vals.get("task_id"):
            qa_ids = self.env["project.task"].browse(vals["task_id"]).mapped("qa_ids")
            project_task = self.env["project.task"].browse(vals["task_id"])
        if project_task:
            if project_task.qa_state_count > 1:
                vals["is_new"] = True
            if not qa_ids and project_task.is_delete is False:
                count = 1
                vals["sequence"] = "TC_" + str(vals.get("task_id")) + "_" + str(count)
            else:
                if project_task.is_delete is True:
                    vals["sequence"] = (
                        "TC_"
                        + str(vals.get("task_id"))
                        + "_"
                        + str(project_task.qa_line_length + 1)
                    )
                    project_task.is_delete = False
                elif project_task.is_delete is False:
                    vals["sequence"] = (
                        "TC_"
                        + str(vals.get("task_id"))
                        + "_"
                        + str(
                            int(
                                qa_ids[len(project_task[0]["qa_ids"]) - 1]["sequence"].split('_')[-1]   # .split('_') : [Fixed] sequence start from 1 after 10
                            )
                            + 1
                        )
                    )
            return super(QualityAnalysis, self).create(vals)

    def unlink(self):
        """Method for getting deleted record details"""

        project_task = self.env["project.task"].search(
            [("id", "=", self[0]["task_id"].id)]
        )
        project_task.is_delete = True
        for rec in self:
            if (
                rec.sequence[-1]
                == project_task[0]["qa_ids"][len(project_task[0]["qa_ids"]) - 1][0][
                    "sequence"
                ][-1]
            ):
                project_task.qa_line_length = rec.sequence[-1]
            elif (
                rec.sequence[-1]
                != project_task[0]["qa_ids"][len(project_task[0]["qa_ids"]) - 1][0][
                    "sequence"
                ][-1]
            ):
                project_task.qa_line_length = project_task[0]["qa_ids"][
                    len(project_task[0]["qa_ids"]) - 1
                ][0]["sequence"][-1]
        return super(QualityAnalysis, self).unlink()
