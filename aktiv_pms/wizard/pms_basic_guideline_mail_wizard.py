from odoo import fields, models


class PmsBasicGuidelineMailWizard(models.TransientModel):
    _name = "pms.basic.guideline.mail.wizard"
    _description = "PMS Basic Guideline Mail Wizard"

    user_type = fields.Selection(
        string="User Type",
        selection=[
            ("developer", "Developer"),
            ("general", "General"),
            ("manager", "Manager"),
        ],
    )

    mail_template_id = fields.Many2one(
        "mail.template",
        string="Email Template",
        domain=[("model", "=", "pms.basic.guideline")],
        help="If set an email will be sent to the user",
    )

    def update_users_by_mail(self):
        """Send Documents update by mail to users as per user type selected"""
        template = self.mail_template_id
        res_id = self._context.get("res_id")
        guideline_id = self.env["pms.basic.guideline"].browse(res_id)
        if not template:
            return
        users = self.env["res.users"].search([])
        user_ids = None
        # filter developers -->
        if self.user_type == "developer":
            user_ids = [
                user.id
                for user in users
                if user.has_group("project.group_project_user")  # developer
                or user.has_group("aktiv_pms.group_aktiv_project_manager")  # manager
            ]
        # filter managers -->
        elif self.user_type == "manager":
            user_ids = [
                user.id
                for user in users
                if user.has_group("aktiv_pms.group_aktiv_project_manager")  # manager
            ]
        # general filter: if selected 'general' in selection field, mail will be
        # sent to  developers, managers, QA, project functional and admin -->
        else:
            user_ids = [
                user.id
                for user in users
                if user.has_group("project.group_project_user")  # developer
                or user.has_group("aktiv_pms.group_aktiv_project_QA")  # QA
                or user.has_group("aktiv_pms.group_aktiv_project_functional")  # funct.
                or user.has_group("aktiv_pms.group_aktiv_project_manager")  # manager
                or user.has_group("base.user_admin")  # admin
            ]
        if user_ids:
            user_ids_to_send_mail = users.filtered(lambda user: user.id in user_ids)
            attach_values = {
                "name": "Document",
                "type": "binary",
                "datas": guideline_id.upload,  # use datas of binary field 'upload'
                "store_fname": guideline_id.upload,
                "mimetype": "application/pdf",
            }
            attach_data = self.env["ir.attachment"].create(attach_values)
            for user in user_ids_to_send_mail:
                email_values = {
                    "email_to": user.login,
                }
                # send mail -->
                template.send_mail(
                    res_id,
                    force_send=True,
                    email_values=email_values,
                )
                # add attachment in mail template
                template.attachment_ids = [(6, 0, [attach_data.id])]
