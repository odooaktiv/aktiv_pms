# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software.
# See LICENSE file for full copyright & licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    colour_scheme_pallet_id = fields.Many2one(
        "colour.scheme.pallet",
        "Color Scheme Pallet",
        domain="[('show_pallet_mode', '!=', 'dark')]",
    )
    dark_colour_scheme_pallet_id = fields.Many2one(
        "colour.scheme.pallet",
        "Dark Color Scheme Pallet",
        domain="[('show_pallet_mode', '!=', 'light')]",
    )
    allow_user_scheme = fields.Boolean("Allow users to select color scheme")
    home_screen_background = fields.Boolean("Apply Home-screen background")
    home_screen_background_style = fields.Selection(
        [
            ("gradiant", "Gradiant (Header & Primary colors)"),
            ("solid", "Solid (Header Color)"),
        ],
        "Apply Home-screen background style",
        default="gradiant",
    )
    is_web_enterprise = fields.Boolean(
        "Is web enterprise installed?",
        compute="_compute_web_enterprise_installed",
    )

    def _compute_web_enterprise_installed(self):
        for rec in self:
            web_enterprise = self.env["ir.module.module"].search(
                [("state", "=", "installed"), ("name", "=", "web_enterprise")]
            )
            rec.is_web_enterprise = False
            if web_enterprise:
                rec.is_web_enterprise = True
