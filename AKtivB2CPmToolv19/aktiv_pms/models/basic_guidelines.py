# -*- coding: utf-8 -*-

from odoo import fields, models


"""
    Add a menu named Basic Guidelines in Project Menu. This menu should be visisble to all the Users.
    Create a tree view which will have the following fields  1) Name - Char 2) Link - Text field 
"""


class ProjectBasicGuideline(models.Model):
    _name = "pms.basic.guideline"
    _description = "Basic Guideline"

    name = fields.Char(string="Name")
    link = fields.Text(string="Link")
    version = fields.Char(string="Version")
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    remarks = fields.Html(
        string="Remarks",
    )
    upload = fields.Binary(
        string="Upload",
        attachment=True,
    )

    def action_open_update_users_wizard(self):
        """open wizard to select user type and mail template for
        sending mail to that user"""
        ctx = {"res_id": self.id}
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "pms.basic.guideline.mail.wizard",
            "views": [(False, "form")],
            "view_id": False,
            "target": "new",
            "context": ctx,
        }
