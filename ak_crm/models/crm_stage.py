# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Stage(models.Model):
    _inherit = "crm.stage"
    _order = "sequence, id"

    type = fields.Many2many("crm.type", string="Type")
    stage_id_type_key = fields.Char(compute="compute_stage_id_type_key", store=True)
    is_lost = fields.Boolean(string="Is Lost Stage")

    @api.depends("type", "type.key")
    def compute_stage_id_type_key(self):
        for rec in self:
            rec.stage_id_type_key = (
                ",".join([k for k in rec.type.mapped("key") if k]) if rec.type else ""
            )

    @api.constrains("is_lost")
    def _check_is_lost(self):
        if self.is_lost:
            lost = self.search([("is_lost", "=", True)])
            if len(lost) > 1:
                raise ValidationError("You can select only single lost stage")
