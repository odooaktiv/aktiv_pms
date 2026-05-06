# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class UrgentTask(models.Model):
    _name = "urgent.task"
    _description = "Urgent Task"

    name = fields.Char(string="Name")
    project_id = fields.Many2one("project.project", string="Project")
    consultant_ids = fields.Many2many(
        "res.users",
        "task_consult_rel",
        "task_id",
        "user_id",
        string=_("Consultant"),
        tracking=True,
    )
    task_affected = fields.Text(string="Task Affected")
    date_assign = fields.Date(string="Assign Date")
    remark = fields.Text(string="Remarks")

    @api.model
    def _valid_field_parameter(self, field, name):
        # Extend valid parameters to include 'tracking' for this model
        if name == 'tracking':
            return True
        return super(UrgentTask, self)._valid_field_parameter(field, name)
