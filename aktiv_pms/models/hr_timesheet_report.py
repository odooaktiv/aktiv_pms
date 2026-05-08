# -*- coding: utf-8 -*-
from odoo import fields, models


class TimesheetsAnalysisReport(models.Model):
    _inherit = 'timesheets.analysis.report'

    state = fields.Selection([
        ('approval', 'Pending For Approval'),
        ('approved', 'Approved'),
    ], string='State', readonly=True)
    checked = fields.Boolean(string='Productive Hours Amends', readonly=True)
    user_type = fields.Selection([
        ('dev', 'Developer'),
        ('qa', 'QA'),
    ], string='User Type', readonly=True)
    data_sync = fields.Selection([
        ('not_sync', 'Not Sync'),
        ('sync', 'Sync'),
    ], string='Timesheet Sync', readonly=True)
    status = fields.Selection([
        ('on_time', 'On Time'),
        ('late', 'Late'),
    ], string='Status', readonly=True)

    def _select(self):
        return super()._select() + ",\n                A.state,\n                A.checked,\n                A.user_type,\n                A.data_sync,\n                A.status"
