# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Lead(models.Model):
    _inherit = "crm.lead"

    consultant_name = fields.Char(string="Consult Name")
    type = fields.Selection(
        selection_add=[("lead", "Email Lead"), ("opportunity",)],
        ondelete={"lead": "set default", "opportunity": "set default"},
        string="Type"
    )
    linkedin_page = fields.Char(string="LinkedIn Page")
    linkedin_profile = fields.Char(string="LinkedIn Profile")
    linkedin_id = fields.Char(string="LinkedIn ID")
    no_of_employees = fields.Char(string="No. of Employees")
    lead_type = fields.Selection(
        [
            ("b2c_inbound", "B2C Inbound"),
            ("b2b_inbound", "B2B Inbound"),
            ("b2b_outbound", "B2B Outbound"),
            ("b2c_outbound", "B2C Outbound"),
        ],
        string="Lead Type",
    )
    technology_ids = fields.Many2many("technology", string="Technology")
    partnership_level = fields.Selection(
        [("ready", "Ready"), ("silver", "Silver"), ("gold", "Gold")],
        string="Partnership Level",
    )
    customer_using_odoo = fields.Selection(
        [("yes", "Yes"), ("no", "No"), ("not_sure", "Not Sure")],
        string="Is The Customer Using Odoo?",
    )
    odoo_edition = fields.Selection(
        [
            ("e_online", "Enterprise-odoo online"),
            ("e_sh", "Enterprise-odoo SH"),
            ("e_onpremise", "Enterprise-On premise"),
            ("community", "Community"),
        ],
        string="Odoo Edition",
    )
    odoo_version_ids = fields.Many2many("odoo.version", string="Odoo Version")
    consultant_ids = fields.Many2many("res.users", string="Consultant")
    fetched_from = fields.Char(string="Fetched From")
    incoming_server_id = fields.Many2one("fetchmail.server", string="Incoming Server")
    crm_stage_type_id = fields.Many2one("crm.type", compute="compute_crm_stage_type_id")
    stage_name = fields.Char(related="stage_id.name")
    custom_stage = fields.Integer()

    @api.model_create_multi
    def create(self, vals_list):
        """Inherit create: send mail to assignee of lead and consultants of opport."""
        res = super(Lead, self).create(vals_list)
        if res.user_id:
            template = self.env.ref("ak_crm.ak_crm_lead_assigned_template")
            if not self._context.get("no_mail_for_opp_conv"):
                email_values = {"email_to": res.user_id.partner_id.email}
                template.send_mail(res.id, force_send=True, email_values=email_values)
        if res.consultant_ids:
            template = self.env.ref("ak_crm.ak_crm_opportunity_template")
            user_ids = res.consultant_ids
            for user in user_ids:
                res.consultant_name = user.name
                email_values = {"email_to": user.partner_id.email}
                template.send_mail(res.id, force_send=True, email_values=email_values)
        return res

    def write(self, values):
        """Inherit write: send mail to assignee of lead and consultants of opport."""
        consult_ids_before = self.consultant_ids.ids
        res = super(Lead, self).write(values)
        consult_ids_after = self.consultant_ids.ids

        # Prevent direct transition to the "lost" stage if no lost reason is provided
        if "stage_id" in values and "lost_reason_id" not in values:
            new_stage_id = values["stage_id"]
            if new_stage_id == self.env.ref('ak_crm.stage_lost').id:
                raise ValidationError(
                    _("You will not be able to move the lead direct lost stage! \n"
                      "Please click the button mark as lost from the dropdown menu!")
                )

        if values.get("user_id") and not self._context.get("no_mail_for_opp_conv"):
            template = self.env.ref("ak_crm.ak_crm_lead_assigned_template")
            email_values = {"email_to": self.user_id.partner_id.email}
            template.send_mail(self.id, force_send=True, email_values=email_values)
        if values.get("consultant_ids"):
            template = self.env.ref("ak_crm.ak_crm_opportunity_template")
            user_ids_to_send_mail = list(
                set(consult_ids_before) ^ set(consult_ids_after)
            )
            user_ids = (
                self.env["res.users"]
                .search([("id", "in", user_ids_to_send_mail)])
                .filtered(lambda user: user.id not in consult_ids_before)
            )
            for user in user_ids:
                self.consultant_name = user.name
                email_values = {"email_to": user.partner_id.email}
                template.send_mail(self.id, force_send=True, email_values=email_values)
        return res

    def redirect_lead_opportunity_view(self):
        """Inherit: set no_mail_for_opp_conv to false from context to send mail"""
        action = super(Lead, self).redirect_lead_opportunity_view()
        action["context"]["no_mail_for_opp_conv"] = False
        return action

    def compute_crm_stage_type_id(self):
        """Used this method to fetch stages"""
        for rec in self:
            rec.crm_stage_type_id = False
            if self._context.get("default_type") == "lead" and (
                rec.lead_type in ["b2c_inbound", "b2b_inbound"]
                or self.fetched_from
                or (self.fetched_from != "" and self._context.get("email_leads"))
            ):
                rec.crm_stage_type_id = self.env.ref("ak_crm.crm_type_lead")
            elif self._context.get("default_type") == "lead" and rec.lead_type in [
                "b2b_outbound",
                "b2c_outbound",
            ]:
                rec.crm_stage_type_id = self.env.ref("ak_crm.crm_type_outbound_lead")
            elif self._context.get("default_type") == "opportunity":
                rec.crm_stage_type_id = self.env.ref("ak_crm.crm_type_opportunity")

    def _convert_opportunity_data(self, customer, team_id=False):
        """Extract the data from a lead to create the opportunity
        :param customer : res.partner record
        :param team_id : identifier of the Sales Team to determine the stage
        """
        new_team_id = team_id if team_id else self.team_id.id
        upd_values = {
            "type": "opportunity",
            "date_open": fields.Datetime.now(),
            "date_conversion": fields.Datetime.now(),
        }
        if customer != self.partner_id:
            upd_values["partner_id"] = customer.id if customer else False
        if not self.stage_id:
            stage = self._stage_find(team_id=new_team_id)
            upd_values["stage_id"] = stage.id
        if self.stage_id:
            stage = self._stage_find(team_id=new_team_id)
            upd_values["stage_id"] = stage.id
        return upd_values

    def _stage_find(self, team_id=False, domain=None, order="sequence", limit=1):
        # collect all team_ids by adding given one, and the ones related to the current leads
        team_ids = set()
        if team_id:
            team_ids.add(team_id)
        for lead in self:
            if lead.team_id:
                team_ids.add(lead.team_id.id)
        search_domain = []
        if self._context.get("default_type") == "opportunity":
            if team_ids:
                search_domain = [
                    "|",
                    ("team_ids", "=", False),
                    ("team_ids", "in", list(team_ids)),
                    ("type", "=", self.env.ref("ak_crm.crm_type_opportunity").id),
                ]
            else:
                search_domain = [
                    "|",
                    ("team_ids", "=", False),
                    ("type", "=", self.env.ref("ak_crm.crm_type_opportunity").id),
                ]
        if self._context.get("email_leads"):
            if team_ids:
                search_domain = [
                    "|",
                    ("team_ids", "=", False),
                    ("team_ids", "in", list(team_ids)),
                    ("type", "=", self.env.ref("ak_crm.crm_type_lead").id),
                ]
            else:
                search_domain = [
                    "|",
                    ("team_ids", "=", False),
                    ("type", "=", self.env.ref("ak_crm.crm_type_lead").id),
                ]
        if self._context.get("outbound_leads"):
            if team_ids:
                search_domain = [
                    "|",
                    ("team_ids", "=", False),
                    ("team_ids", "in", list(team_ids)),
                    ("type", "=", self.env.ref("ak_crm.crm_type_outbound_lead").id),
                ]
            else:
                search_domain = [
                    "|",
                    ("team_ids", "=", False),
                    ("type", "=", self.env.ref("ak_crm.crm_type_outbound_lead").id),
                ]
        if self._context.get("default_type") == "lead":
            if team_ids:
                search_domain = [
                    "|",
                    ("team_ids", "=", False),
                    ("team_ids", "in", list(team_ids)),
                ]
            else:
                search_domain = [("team_ids", "=", False)]

        if domain:
            search_domain += list(domain)
        # perform search, return the first found
        return self.env["crm.stage"].search(search_domain, order=order, limit=limit)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Used this method group for leads and opportunity"""
        group_stages = super()._read_group_stage_ids(stages, domain)
        if self._context.get("email_leads", False):
            group_stages = group_stages.filtered(
                lambda stage: self.env.ref("ak_crm.crm_type_lead").id
                in stage.type.ids
            )
        if self._context.get("outbound_leads", False):
            group_stages = group_stages.filtered(
                lambda stage: self.env.ref("ak_crm.crm_type_outbound_lead").id
                in stage.type.ids
            )
        if self._context.get("default_type") == "opportunity":
            group_stages = group_stages.filtered(
                lambda stage: self.env.ref("ak_crm.crm_type_opportunity").id
                in stage.type.ids
            )
        return group_stages

    @api.onchange("lead_type")
    def _onchange_lead_type(self):
        if self.lead_type:
            if (
                self.lead_type
                in ["b2c_inbound", "b2b_inbound", "b2b_outbound", "b2c_outbound"]
                and not self.type == "opportunity"
            ):
                self.type = "lead"
            else:
                self.type = "opportunity"
            type_name = dict(self._fields["type"].selection).get(self.type)
            if self.lead_type in ["b2b_outbound", "b2c_outbound"]:
                crm_types = self.env.ref("ak_crm.crm_type_outbound_lead")
            else:
                crm_types = self.env["crm.type"].search([("name", "=", type_name)], limit=1)
            stage_id = self.env["crm.stage"].search([("type", "=", crm_types.id)])
            if stage_id:
                self.stage_id = stage_id[0]
            return {"domain": {"stage_id": [("type", "=", crm_types.id)]}}

    def change_stage(self):
        for lead in self:
            lead.stage_id = self.env.ref("ak_crm.stage_lead16")

    @api.onchange("stage_id")
    def onchange_stage_id_custom(self):
        """Click the cancel button to move lead the previous stage"""
        lead = self._origin
        lead.write({"custom_stage": lead.stage_id.id})
        if not self.stage_id == self.env.ref("ak_crm.stage_lost"):
            self.write({"lost_reason_id": False})
        if self.stage_id.id == self.env.ref(
            "ak_crm.stage_lost"
        ).id and self._context.get("kanban_lost_stage"):
            raise ValidationError(
                _(
                    "You will not be able to move the lead direct lost stage! \nPlease click the button mark as lost from the dropdown menu!"
                )
            )
        if self.stage_id.id == self.env.ref(
            "ak_crm.stage_lost"
        ).id and self._context.get("form_lost_stage"):
            raise ValidationError(
                _("You will not be able to move the lead direct lost stage")
            )

    def action_lead_lost(self):
        action_id = self.env.ref("crm.crm_lead_lost_view_form").id
        return {
            "type": "ir.actions.act_window",
            "res_model": "crm.lead.lost",
            "view_type": "form",
            "view_mode": "form",
            "view_id": action_id,
            "name": "Lost Reason",
            "target": "new",
        }
