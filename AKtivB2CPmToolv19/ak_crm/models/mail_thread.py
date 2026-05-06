# -*- coding: utf-8 -*-

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        data = {}
        if isinstance(custom_values, dict):
            data = custom_values.copy()
            if self._name == "crm.lead":
                data.update({"stage_id": self.env.ref("ak_crm.stage_lead22").id})
        fields = self.fields_get()
        name_field = self._rec_name or "name"
        to_field = "fetched_from"
        res = self.env["fetchmail.server"].search(
            [("user", "=", msg_dict.get("recipients", ""))]
        )
        incoming_field = "incoming_server_id"
        if name_field and to_field in fields:
            data[name_field] = msg_dict.get("subject", "")
            if msg_dict.get("to") in [
                "odoo@aktivsoftware.com",
                "sales@aktivsoftware.com",
                "Sales@aktivsoftware.com",
            ]:
                data[to_field] = msg_dict.get("to")
            else:
                fetch_mail = msg_dict.get("to")
                mail_split = fetch_mail[fetch_mail.find("<") + 1 : fetch_mail.find(">")]
                if mail_split in [
                    "odoo@aktivsoftware.com",
                    "sales@aktivsoftware.com",
                    "Sales@aktivsoftware.com",
                ]:
                    data[to_field] = mail_split
            data[incoming_field] = res.id
        return self.create(data)

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        res = super(MailThread, self)._message_auto_subscribe_followers(updated_values, default_subtype_ids)

        field = self._fields.get("user_id")
        consultant_commands = updated_values.get("consultant_ids")
        user_id = updated_values.get("user_id")

        if consultant_commands:
            # Check if consultant_commands contain Command objects, and extract the IDs
            user_ids = [
                cmd[1] for cmd in consultant_commands if isinstance(cmd, (list, tuple)) and cmd[0] == 4
            ]  # Command (4, id, 0) for adding a record

            if user_ids and field.comodel_name == "res.users":
                for user in user_ids:
                    user_rec = self.env["res.users"].sudo().browse(user)
                    try:
                        if user_rec.active:
                            res.append(
                                (
                                    user_rec.partner_id.id,
                                    default_subtype_ids,
                                    "mail.message_user_assigned"
                                    if user_rec != self.env.user else False,
                                )
                            )
                    except Exception:
                        pass

        return res


    def _get_message_create_valid_field_names(self):
        res = super(MailThread, self)._get_message_create_valid_field_names()
        res.update({'mail_to'})
        return res
