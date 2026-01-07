from odoo import fields, models


class MailMail(models.Model):
    _inherit = "mail.mail"

    lead_ids = fields.Many2many("crm.lead", string="Lead")
