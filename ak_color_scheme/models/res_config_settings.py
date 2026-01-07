# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software.
# See LICENSE file for full copyright & licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    colour_scheme_pallet_id = fields.Many2one(
        related="company_id.colour_scheme_pallet_id",
        readonly=False,
    )
    dark_colour_scheme_pallet_id = fields.Many2one(
        related="company_id.dark_colour_scheme_pallet_id",
        readonly=False,
    )
    allow_user_scheme = fields.Boolean(
        related="company_id.allow_user_scheme",
        string="Allow users to select color scheme",
        readonly=False,
    )
    home_screen_background = fields.Boolean(
        related="company_id.home_screen_background",
        string="Apply Home-screen background",
        readonly=False,
    )
    home_screen_background_style = fields.Selection(
        related="company_id.home_screen_background_style",
        string="Apply Home-screen Background Style",
        readonly=False,
    )
    is_web_enterprise = fields.Boolean(
        related="company_id.is_web_enterprise",
        string="Is web enterprise installed? ",
    )

    # Light Color Schema
    primary_color = fields.Char(
        related="colour_scheme_pallet_id.primary_color",
    )
    primary_color_font = fields.Char(
        related="colour_scheme_pallet_id.primary_color_font",
    )
    secondary_color = fields.Char(
        related="colour_scheme_pallet_id.secondary_color",
    )
    secondary_color_font = fields.Char(
        related="colour_scheme_pallet_id.secondary_color_font",
    )
    header_color = fields.Char(
        related="colour_scheme_pallet_id.header_color",
    )
    header_color_font = fields.Char(
        related="colour_scheme_pallet_id.header_color_font",
    )
    darker_primary = fields.Boolean(
        related="colour_scheme_pallet_id.darker_primary",
    )
    darker_secondary = fields.Boolean(
        related="colour_scheme_pallet_id.darker_secondary",
    )

    # Dark Color Schema
    primary_color_dark = fields.Char(
        related="dark_colour_scheme_pallet_id.primary_color",
        string="Primary Color(Dark)",
    )
    primary_color_font_dark = fields.Char(
        related="dark_colour_scheme_pallet_id.primary_color_font",
        string="Primary Font Color(Dark)",
    )
    secondary_color_dark = fields.Char(
        related="dark_colour_scheme_pallet_id.secondary_color",
        string="Secondary Color(Dark)",
    )
    secondary_color_font_dark = fields.Char(
        related="dark_colour_scheme_pallet_id.secondary_color_font",
        string="Secondary Font Color(Dark)",
    )
    header_color_dark = fields.Char(
        related="dark_colour_scheme_pallet_id.header_color",
        string="Header Color(Dark)",
    )
    header_color_font_dark = fields.Char(
        related="dark_colour_scheme_pallet_id.header_color_font",
        string="Header Font Color(Dark)",
    )
    darker_primary_dark = fields.Boolean(
        related="dark_colour_scheme_pallet_id.darker_primary",
        string="Is primary color darker than primary font color? ",
    )
    darker_secondary_dark = fields.Boolean(
        related="dark_colour_scheme_pallet_id.darker_secondary",
        string="Is secondary color darker than secondary font color? ",
    )

    @api.onchange("colour_scheme_pallet_id")
    def _onchange_colour_scheme_pallet_id(self):
        for wizard in self:
            pallet = wizard.colour_scheme_pallet_id
            wizard.company_id.colour_scheme_pallet_id = pallet
            wizard.update(
                {
                    "primary_color": pallet.primary_color,
                    "primary_color_font": pallet.primary_color_font,
                    "secondary_color": pallet.secondary_color,
                    "secondary_color_font": pallet.secondary_color_font,
                    "header_color": pallet.header_color,
                    "header_color_font": pallet.header_color_font,
                    "darker_primary": pallet.darker_primary,
                    "darker_secondary": pallet.darker_secondary,
                }
            )

    @api.onchange("dark_colour_scheme_pallet_id")
    def _onchange_dark_colour_scheme_pallet_id(self):
        for wizard in self:
            pallet = wizard.dark_colour_scheme_pallet_id
            wizard.company_id.dark_colour_scheme_pallet_id = pallet
            wizard.update(
                {
                    "primary_color_dark": pallet.primary_color,
                    "primary_color_font_dark": pallet.primary_color_font,
                    "secondary_color_dark": pallet.secondary_color,
                    "secondary_color_font_dark": pallet.secondary_color_font,
                    "header_color_dark": pallet.header_color,
                    "header_color_font_dark": pallet.header_color_font,
                    "darker_primary_dark": pallet.darker_primary,
                    "darker_secondary_dark": pallet.darker_secondary,
                }
            )

    def create_color_scheme_pallet(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "ak_color_scheme.action_color_scheme_pallet_configurator"
        )
        dark_color_pallet = self._context.get("dark_color_pallet", False)
        action.update(
            {
                "name": "Create Color Scheme Pallet",
                "context": {
                    "default_company_id": self.env.company.id,
                    "default_show_pallet_mode": (
                        "dark" if dark_color_pallet else "light"
                    ),
                    "dark_color_pallet": dark_color_pallet,
                },
                "target": "new",
                "view_mode": "form",
                "views": [
                    [
                        self.env.ref(
                            "ak_color_scheme.view_color_scheme_pallet_form"
                        ).id,
                        "form",
                    ]
                ],
            }
        )
        return action

    def update_color_scheme_pallet(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "ak_color_scheme.action_color_scheme_pallet_configurator"
        )
        res_id = self.env.company.colour_scheme_pallet_id.id
        if self._context.get("dark_color_pallet", False):
            res_id = self.env.company.dark_colour_scheme_pallet_id.id
        action.update(
            {
                "name": "Update Color Scheme Pallet",
                "target": "new",
                "view_mode": "form",
                "views": [
                    [
                        self.env.ref(
                            "ak_color_scheme.view_color_scheme_pallet_form"
                        ).id,
                        "form",
                    ]
                ],
                "res_id": res_id,
            }
        )
        return action

    def reset_color_scheme_pallet(self):
        self.colour_scheme_pallet_id = False
        self.dark_colour_scheme_pallet_id = False
        self.allow_user_scheme = False
        self.home_screen_background = False
