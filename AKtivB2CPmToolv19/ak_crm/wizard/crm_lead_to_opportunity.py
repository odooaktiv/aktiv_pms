from odoo import models


class Lead2OpportunityPartnerInherit(models.TransientModel):
    """Lead2OpportunityPartnerInherit"""

    _inherit = "crm.lead2opportunity.partner"

    def action_apply(self):
        """Override to send mail if user id exists."""
        user = self.user_id
        active_id = self._context.get("active_id")
        lead_id = self.env["crm.lead"].browse(active_id)
        user_id = lead_id.user_id.id
        if self.name == "merge":
            result_opportunity = self.with_context(
                tracking_disable=True
            )._action_merge()
        else:
            result_opportunity = self.with_context(
                tracking_disable=True
            )._action_convert()
        if (user and user_id and user.id != user_id) or (user and not user_id):
            template = self.env.ref(
                "ak_crm.ak_crm_converted_to_opportunity_template"
            )
            email_values = {"email_to": user.partner_id.email}
            template.send_mail(
                self.lead_id.id, force_send=True, email_values=email_values
            )
        return result_opportunity.redirect_lead_opportunity_view()
