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

    def _get_message_format_fields(self):
        return [
            "id",
            "body",
            "date",
            "author_id",
            "email_from",  # base message fields
            "message_type",
            "subtype_id",
            "subject",
            "crm_type",  # message specific
            "model",
            "mail_to",
            "res_id",
            "record_name",  # document related
            "partner_ids",  # recipients
            "starred_partner_ids",  # list of partner ids for whom the message is starred
        ]
