from odoo import api, fields, models


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    old_db_id = fields.Integer(string="Old DB ID", copy=False)
    sop_stage = fields.Boolean()
    user_id = fields.Many2one('res.users', 'Stage Owner', default=False, compute='_compute_user_id', store=True, index=True)
    project_ids = fields.Many2many('project.project', 'project_task_type_rel', 'type_id', 'project_id', string='Projects',
        default=lambda self: self._get_default_project_ids())

    def _compute_user_id(self):
        pass

    def create(self, vals):
        context = self.env.context
        if context.get('sop_bank'):
            vals['project_ids'] = [(6, 0, [self.env.ref('ak_project_todo.project_sop_bank').id])]
            vals['sop_stage'] = True
        return super(ProjectTaskType, self).create(vals)
