# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import timedelta


class ResUser(models.Model):
    _inherit = "res.users"

    user_name = fields.Char(string="User Name", copy=False)
    pwd = fields.Char(string="Password", copy=False)
    edit_access_grant_date = fields.Date(string="Edit Access Granted Date")
    approve_access_grant_date = fields.Date(string="Approve Access Granted Date")

    def _get_restricted_group(self):
        return {
            "project.group_project_manager",
            "aktiv_pms.group_aktiv_project_manager",
            "aktiv_pms.group_aktiv_project_team_leader",
            "aktiv_pms.group_aktiv_project_functional",
            "aktiv_pms.group_aktiv_project_QA"
        }

    def _get_restricted_manager_group(self):
        return {
            "project.group_project_manager",
            "aktiv_pms.group_aktiv_project_manager",
            "aktiv_pms.group_aktiv_project_functional",
        }

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        context = self._context
        project_model = self.env['project.project']
        user_ids = []

        def get_project_and_map(context_key, map_fields):
            project_id = project_model.browse(context[context_key])
            ids = []
            for field in map_fields:
                ids.extend(project_id.mapped(field).ids)
            result = list(set(ids))
            return result

        if context.get("for_dev"):
            user_ids = get_project_and_map("for_dev", ["developer_ids"])
        elif context.get("for_qa"):
            user_ids = get_project_and_map("for_qa", ["task_qa_ids"])
        elif context.get("for_cr"):
            user_ids = get_project_and_map("for_cr", ["code_reviewer_ids"])
        elif context.get("urgent_task"):
            user_ids = get_project_and_map("urgent_task", ["user_id", "consultant_ids"])

        if user_ids:
            domain += [('id', 'in', user_ids)]
        return super()._name_search(name, domain, operator, limit, order)



    def write(self, vals):
        group_edit = self.env.ref('aktiv_pms.group_allow_edit_old_timesheets', raise_if_not_found=False)
        group_approve = self.env.ref('aktiv_pms.group_allow_approve_old_timesheets', raise_if_not_found=False)

        res = super(ResUser, self).write(vals)

        if not group_edit and not group_approve:
            return res

        for user in self:
            if group_edit:
                if group_edit in user.group_ids and not user.edit_access_grant_date:
                    user.write({'edit_access_grant_date': fields.Date.today()})
                elif group_edit not in user.group_ids and user.edit_access_grant_date:
                    user.write({'edit_access_grant_date': False})

            if group_approve:
                if group_approve in user.group_ids and not user.approve_access_grant_date:
                    user.write({'approve_access_grant_date': fields.Date.today()})
                elif group_approve not in user.group_ids and user.approve_access_grant_date:
                    user.write({'approve_access_grant_date': False})

        return res

    @api.model
    def revoke_group_access(self):
        param_days = self.env['ir.config_parameter'].sudo().get_param('aktiv_pms.revoke_group_access')
        try:
            revoke_days = int(param_days)
        except (TypeError, ValueError):
            revoke_days = 0
        if revoke_days <= 0:
            return

        cutoff = fields.Date.today() - timedelta(days=revoke_days)
        group_edit = self.env.ref('aktiv_pms.group_allow_edit_old_timesheets')
        group_approve = self.env.ref('aktiv_pms.group_allow_approve_old_timesheets')

        users = self.search(['|',
                             ('edit_access_grant_date', '<=', cutoff),
                             ('approve_access_grant_date', '<=', cutoff),
                             ])
        for user in users:
            if user.edit_access_grant_date and user.edit_access_grant_date <= cutoff:
                if group_edit in user.group_ids:
                    user.group_ids = [(3, group_edit.id)]
                user.edit_access_grant_date = False
            if user.approve_access_grant_date and user.approve_access_grant_date <= cutoff:
                if group_approve in user.group_ids:
                    user.group_ids = [(3, group_approve.id)]
                user.approve_access_grant_date = False
