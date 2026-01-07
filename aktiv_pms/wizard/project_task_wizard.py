# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class ProjectTaskWizard(models.TransientModel):
    _name = "project.task.wizard"
    _description = "Project Task Wizard"

    text = fields.Text(string="Reason", required=True)

    def submit_reason(self):
        rec = self.env['project.task'].browse(self.env.context.get('active_id'))
        message = _("Reason for On Hold : %s") % self.text
        rec.message_post(body=message)
        rec.write({'state': 'on_hold'})
