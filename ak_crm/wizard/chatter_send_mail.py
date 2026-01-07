# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.tools import is_html_empty
from odoo.tools.misc import clean_context


class ChatterSendMail(models.TransientModel):
    _name = "chatter.send.mail"
    _description = "Chatter Send a Mail"
    _mail_flat_thread = True

    email_to = fields.Char(
        string=_("Email To"),
        default=lambda self: self.env["crm.lead"]
        .browse(self._context.get("default_res_id"))
        .email_from,
    )
    email_cc = fields.Char(
        string=_("Email CC"),
        default=lambda self: self.env["crm.lead"]
        .browse(self._context.get("default_res_id"))
        .email_cc,
    )
    subject = fields.Char(
        string=_("Subject"),
        compute='_compute_subject', readonly=False, store=True,
    )
    body = fields.Html(
        string=_("Contents"), render_engine="qweb", sanitize_style=True,
        compute='_compute_body', readonly=False, store=True
    )
    attachment_ids = fields.Many2many("ir.attachment", string=_("Attachments"))
    template_id = fields.Many2one(
        "mail.template",
        string=_("Template"),
        index=True,
        domain="[('model', '=', 'crm.lead')]",
    )
    message_type = fields.Selection(
        [("comment", "Comment"), ("notification", "System notification")],
        "Type",
        required=True,
        default="comment",
        help="Message type: email for email message, notification for system "
        "message, comment for other messages such as user replies",
    )
    subtype_id = fields.Many2one(
        "mail.message.subtype",
        "Subtype",
        ondelete="set null",
        index=True,
        default=lambda self: self.env["ir.model.data"]._xmlid_to_res_id(
            "mail.mt_comment"
        ),
    )

    @api.model
    def _valid_field_parameter(self, field, name):
        # Extend valid parameters to include 'render_engine' for this model
        if name == 'render_engine':
            return True
        return super(ChatterSendMail, self)._valid_field_parameter(field, name)

    def _set_value_from_template(self, template_fname, composer_fname=False):
        """ Set composer value from its template counterpart. In monorecord
        comment mode, we get directly the rendered value, giving the real
        value to the user. Otherwise we get the raw (unrendered) value from
        template, as it will be rendered at send time (for mass mail, whatever
        the number of contextual records to mail) or before posting on records
        (for comment in batch).

        :param str template_fname: name of field on template model, used to
          fetch the value (and maybe render it);
        :param str composer_fname: name of field on composer model, when field
          names do not match (e.g. body_html on template used to populate body
          on composer);
        """
        self.ensure_one()
        composer_fname = composer_fname or template_fname

        # fetch template value, check if void
        template_value = self.template_id[template_fname] if self.template_id else False
        if template_value and template_fname == 'body_html':
            template_value = template_value if not is_html_empty(template_value) else False

        if template_value:
            self[composer_fname] = self.template_id[template_fname]
        return self[composer_fname]


    @api.depends('template_id')
    def _compute_body(self):
        """ Computation is coming either from template, either reset. When
        having a template with a value set, copy it (in batch mode) or render
        it (in monorecord comment mode) on the composer. When removing the
        template, reset it. """
        for composer in self:
            if composer.template_id:
                composer._set_value_from_template('body_html', 'body')
            if not composer.template_id:
                composer.body = False



    @api.depends('template_id')
    def _compute_subject(self):
        """ Computation is coming either form template, either from context.
        When having a template with a value set, copy it (in batch mode) or
        render it (in monorecord comment mode) on the composer. Otherwise
        it comes from the parent (if set), or computed based on the generic
        '_message_compute_subject' method in monorecord comment mode, or
        set to False. When removing the template, reset it. """
        for composer in self:
            if composer.template_id:
                composer._set_value_from_template('subject')

    # @api.onchange("template_id")
    # def _onchange_chatter_template_id(self, **kwargs):
    #     """Fetch body of the template selected from wizard"""
    #     self.ensure_one()
    #     mail_compose = self.env["mail.compose.message"].sudo()
    #     res_id = kwargs.get(
    #         "res_id", self.ids and self.ids[0] or self._context.get("default_res_id")
    #     )
    #     if self.template_id:
    #         update_values = mail_compose._onchange_template_id(
    #             self.template_id.id,
    #             self._context.get("default_res_model"),
    #             self._context.get("default_res_id"),
    #             res_id,
    #         )["value"]
    #         self.update(
    #             {
    #                 "body": update_values.get("body"),
    #                 "subject": update_values.get("subject"),
    #             }
    #         )

    def prepare_message_vals(self, parent_id, subtype_id, lead):
        """Prepare vals of mail.message"""
        return {
            "author_id": self.env.user.partner_id.id,
            "email_from": (
                self.env.user.email_formatted
                or self.env.ref("base.user_root").email_formatted
            ),
            "email_to": self.email_to,
            "email_cc": self.email_cc,
            "parent_id": self.chatter_message_parent_id(parent_id),
            "body": self.body,
            "subject": self.subject,
            "message_type": "comment",
            "subtype_id": subtype_id,
            "add_sign": not bool(self.template_id),
            "record_name": lead.display_name,
            "mail_to": self.email_to,
        }

    def prepare_mail_vals(self, new_message, references):
        """Prepare vals of mail.mail"""
        return {
            "body_html": self.body,
            "email_to": self.email_to,
            "email_cc": self.email_cc,
            "subject": self.subject,
            "mail_message_id": new_message.id,
            "mail_server_id": False,
            "auto_delete": False,
            "references": references,
            "attachment_ids": [(4, att.id) for att in self.attachment_ids],
            "headers": {
                "X-Odoo-Objects": "%s-%s"
                % (
                    self._context.get("default_res_model"),
                    self._context.get("default_res_id"),
                )
            },
        }

    def action_chatter_send_mail(self, parent_id=False):
        """Process the wizard content and send mail without partner creation from crm lead"""
        lead = self.env["crm.lead"].browse(self._context.get("default_res_id"))
        if self.subtype_id:
            subtype_id = self.subtype_id.id
        message_vals = self.prepare_message_vals(parent_id, subtype_id, lead)

        message_vals = dict((key, val) for key, val in message_vals.items() if key in self.env['mail.message']._fields)
        new_message = lead.message_post(**message_vals)

        # Generate references from parent_id
        message_sudo = new_message.sudo()
        if message_sudo.parent_id:
            references = (
                f"{message_sudo.parent_id.message_id} {message_sudo.message_id}"
            )
        else:
            references = message_sudo.message_id

        mail_vals = self.prepare_mail_vals(new_message, references)
        self.env["mail.mail"].sudo().with_context(clean_context(self._context)).create(
            mail_vals
        ).send()
        if self.attachment_ids and message_vals and mail_vals:
            self.env["ir.attachment"].create(
                {"name": attch.name, "type": attch.type, "datas": attch.datas}
                for attch in self.attachment_ids
            )

    def chatter_message_parent_id(self, parent_id):
        """Fetch parent_id of mail.message"""
        MailMessage_sudo = self.env["mail.message"].sudo()
        if self._mail_flat_thread and not parent_id:
            parent_message = MailMessage_sudo.search(
                [
                    ("res_id", "=", self._context.get("default_res_id")),
                    ("model", "=", self._context.get("default_res_model")),
                    ("message_type", "!=", "user_notification"),
                ],
                order="id ASC",
                limit=1,
            )
            parent_id = parent_message.id if parent_message else False
        elif parent_id:
            current_ancestor = MailMessage_sudo.search(
                [("id", "=", parent_id), ("parent_id", "!=", False)]
            )
            if self._mail_flat_thread:
                if current_ancestor:
                    # avoid loops when finding ancestors
                    processed_list = []
                    while (
                        current_ancestor.parent_id
                        and current_ancestor.parent_id not in processed_list
                    ):
                        processed_list.append(current_ancestor)
                        current_ancestor = current_ancestor.parent_id
                    parent_id = current_ancestor.id
            else:
                parent_id = (
                    current_ancestor.parent_id.id
                    if current_ancestor.parent_id
                    else parent_id
                )
        return parent_id
