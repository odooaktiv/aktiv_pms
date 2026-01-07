# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class SopAssignmentWizard(models.TransientModel):
    _name = "sop.assignment.wizard"
    _description = "Assign SOP to Users"

    user_ids = fields.Many2many("res.users", string="Users")
    tag_ids = fields.Many2many("project.tags", string="Tags", domain=[("is_sop_bank", "=", True)])
    task_ids = fields.Many2many(
        "project.task",
        string="SOP Documents",
        domain=[("is_sop_bank", "=", True),("stage_id.name", "=", "Published")]
    )

    @api.onchange('tag_ids')
    def _onchange_tag_ids(self):
        """ Assign SOP Documents based on Tags """
        self.task_ids = False
        if self.tag_ids:
            tasks = self.env['project.task'].search([
                ('tag_ids', 'in', self.tag_ids.ids),
                ('is_sop_bank', '=', True),
                ('active', '=', True),
                ('stage_id.name', '=', 'Published')
            ])
            self.task_ids = tasks

    def action_assign_users(self):
        for task in self.task_ids:
            partner_ids = self.user_ids.mapped("partner_id").ids
            # Keep only new followers (avoid duplicates)
            new_partners_ids = list(set(partner_ids) - set(task.message_partner_ids.ids))
            if not new_partners_ids:
                continue
            # Subscribe new followers
            task.message_subscribe(partner_ids=new_partners_ids)
            # Subscribe new followers
            new_partners = self.env["res.partner"].browse(new_partners_ids)
            user_names = ", ".join(new_partners.mapped("name"))
            # Send mail notification (same as "Add Followers" wizard)
            task.message_notify(
                partner_ids=new_partners_ids,
                subject=f"Invitation to follow Task: : {task.name}",
                body=f"Hello,\n"
                     f"Administrator invited you to follow Task document: {task.name}",
                record_name=task.display_name,
                model=task._name,
                res_id=task.id,
            )
            # Log in chatter for tracking
            task.message_post(
                body=f"Invited Users: {user_names}",
                subtype_xmlid="mail.mt_note"
            )
