# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SupportPack(models.Model):
    _name = "support.pack"
    _description = "Support Pack"

    name = fields.Char("Description")
    project_id = fields.Many2one("project.project", string="project")
    planned_hours = fields.Float("Support Planned Hours")
    start_date = fields.Date("Start Date")

    @api.onchange("start_date")
    def _onchange_date_start(self):
        """Method to call when there is change in the start Date"""
        if self.start_date and self.project_id.date_start and (self.start_date < self.project_id.date_start):
            raise ValidationError(_("Please select date greater than start date!"))
