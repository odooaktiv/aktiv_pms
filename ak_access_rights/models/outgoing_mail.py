# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from lxml import etree
from odoo import fields, models


_logger = logging.getLogger(__name__)


class IrMailServer(models.Model):
    """Inherited: Outgoing Mail Server

    Outgoing Mail Server extension to widen the visibility of the
    SMTP credential fields and to hide the SMTP password field for
    the admin user when the form view is rendered.
    """

    _inherit = "ir.mail_server"

    smtp_user = fields.Char(
        string="Username",
        help="Optional username for SMTP authentication",
        groups="base.group_user",
    )
    smtp_pass = fields.Char(
        string="Password",
        help="Optional password for SMTP authentication",
        groups="base.group_user",
    )

    def get_view(self, view_id=None, view_type="form", **options):
        """Define: Get View

        Override the standard `get_view` to hide the `smtp_pass`
        field on the form view when the current user is the admin
        user. The field is hidden client side by applying an inline
        `display:none;` style to its XML node.

        :param view_id: Identifier of the view to load, or None to
            use the default view of the requested type.
        :param str view_type: Type of the view to return when
            `view_id` is not provided (e.g. ``'form'``, ``'list'``).
        :param options: Additional options forwarded to the parent
            implementation.
        :return: Dictionary describing the requested view, with the
            `smtp_pass` node updated when applicable.
        :rtype: dict
        :raise: None
        """
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == "form":
            doc = etree.XML(res["arch"])
            for node in doc.xpath("//field[@name='smtp_pass']"):
                if self.env.ref("base.user_admin").id == self.env.user.id:
                    node.set("style", "display:none;")
            res["arch"] = etree.tostring(doc, encoding="unicode")
        return res
