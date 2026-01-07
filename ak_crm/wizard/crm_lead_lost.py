# -*- coding: utf-8 -*-

from odoo import api, fields, models


class CrmLeadLost(models.TransientModel):
    _inherit = "crm.lead.lost"

    def action_lost_reason_apply(self):
        if self._context.get("kanban_view_lead_lost") or self._context.get(
            "form_view_lead_lost"
        ):
            leads = self.env["crm.lead"].browse(self._context.get("active_id"))
            leads.write(
                {
                    "lost_reason_id": self.lost_reason_id.id,
                    "stage_id": self.env.ref("ak_crm.stage_lost").id,
                }
            )
            leads.action_set_lost(lost_reason_id=self.lost_reason_id.id)
            leads.active = True
            if self._context.get("kanban_view_lead_lost"):
                return {"type": "ir.actions.client", "tag": "reload"}
        else:
            return super(CrmLeadLost, self).action_lost_reason_apply()
