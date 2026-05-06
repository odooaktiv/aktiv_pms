# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountAnalyticLineWizard(models.TransientModel):
    _name = "account.analytic.line.wizard"
    _description = "Analytic Line Wizard"

    @api.model
    def default_get(self, fields):
        res = super(AccountAnalyticLineWizard, self).default_get(fields)
        if self._context.get('active_id') and self._context.get('active_model') == 'account.analytic.line':
            line = self.env['account.analytic.line'].browse(self._context.get('active_id'))
            res['approved_hours'] = line.remaining_hours
        return res

    text = fields.Text(string="Reason", required=True)
    approved_hours = fields.Float(string="Productive Hours", required=True)

    def submit_reason(self):
        self.ensure_one()
        line = self.env['account.analytic.line'].browse(self.env.context.get('active_id'))
        if not line.task_id:
            raise ValidationError(
                _(
                    "Task is not found for this entry!"
                )
            )
        message = _("Reason for Approval : {} <br/> Employee : {}").format(self.text, line.employee_id.name, ) + _(
            '<br/> Productive Hours : {0:02.0f}:{1:02.0f}'.format(
                *divmod(line.approved_hours * 60, 60)) + " ➡ " + '{0:02.0f}:{1:02.0f}'.format(
                *divmod(self.approved_hours * 60, 60)))
        line.task_id.message_post(body=Markup(message))
        return line.with_context(skip_lock_check=True).write({
                'approved_hours': self.approved_hours,
                'state': "approved",
                'remaining_hours': 0,
                'checked': True,
                'last_approval_reason': self.text,
                'last_approver_id': self.env.user.id,
                'hide_timesheet_approve_btn': True
            })
