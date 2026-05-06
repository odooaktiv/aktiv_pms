# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class Invite(models.TransientModel):
    """ Wizard to invite partners (or channels) and make them followers. """

    _inherit = "mail.followers.edit"

    group_ids = fields.Many2many("discuss.channel", string="Groups/Channels")

    @api.onchange("group_ids")
    def onchange_gruop_ids(self):
        if self.group_ids:
            self.partner_ids = [
                (
                    6,
                    0,
                    self.group_ids.mapped("channel_partner_ids")
                    .ids,
                )
            ]
