# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class Message(models.Model):
    _inherit = "mail.message"

    crm_type = fields.Char(
        string=_("CRM Type"), compute="_compute_crm_type", store=True
    )
    mail_to = fields.Char(string=_("Mail To"))

    @api.depends("model", "res_id")
    def _compute_crm_type(self):
        self.crm_type = False
        for rec in self:
            if rec.model == "crm.lead":
                rec.crm_type = self.env["crm.lead"].browse(rec.res_id).type

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + ["crm_type", "mail_to"]
