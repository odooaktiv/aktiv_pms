# -*- coding: utf-8 -*-

from odoo import fields, models


class QualityCheckPoints(models.Model):
    _name = "quality.check.points"
    _description = "Quality Check Points"

    name = fields.Char(string="Name")
    is_required = fields.Boolean(string="Required ?")
    is_done = fields.Boolean(string="Done")
    task_id = fields.Many2one("project.task", string="Task", index=True)
