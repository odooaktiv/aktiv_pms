# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class TaskType(models.Model):
    _name = "task.type"
    _description = "Task Type"

    name = fields.Char("Name", required=True)
