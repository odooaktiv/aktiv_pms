# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ReportProjectTaskUser(models.Model):
    _inherit = 'report.project.task.user'

    task_type_id = fields.Many2one('task.type', string='Task Type', readonly=True)
    urgent_task = fields.Boolean(string='Urgent Task', readonly=True)

    def _select(self):
        return super()._select() + ",\n                t.task_type_id,\n                t.urgent_task"

    def _group_by(self):
        return super()._group_by() + ",\n                t.task_type_id,\n                t.urgent_task"

    def init(self):
        # Explicitly recreate the SQL view so the custom columns are included
        # when aktiv_pms is upgraded (Odoo only auto-calls init() for the defining module).
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW %s AS
                 SELECT %s
                   FROM %s
                  WHERE %s
               GROUP BY %s
        """ % (self._table, self._select(), self._from(), self._where(), self._group_by()))
