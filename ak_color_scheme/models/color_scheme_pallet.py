# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software.
# See LICENSE file for full copyright & licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ColorSchemePallet(models.Model):
    _name = "colour.scheme.pallet"
    _description = "Color Scheme Pallets"

    name = fields.Char("Pallet Name", required=True)
    company_id = fields.Many2one("res.company")
    primary_color = fields.Char("Primary Color", required=True)
    primary_color_font = fields.Char("Primary Font Color", required=True)
    secondary_color = fields.Char("Secondary Color", required=True)
    secondary_color_font = fields.Char("Secondary Font Color", required=True)
    header_color = fields.Char("Header Color", required=True)
    header_color_font = fields.Char("Header Font Color", required=True)
    darker_primary = fields.Boolean(
        "Is primary color darker than primary font color?"
    )
    darker_secondary = fields.Boolean(
        "Is secondary color darker than secondary font color?"
    )
    show_pallet_mode = fields.Selection(
        [("light", "Light"), ("dark", "Dark"), ("both", "Both")],
        string="Show Pallet Mode",
        default="both",
    )

    @api.constrains("name", "company_id")
    def _check_unique_pallet(self):
        pallet_record = self.search(
            [
                ("company_id", "in", [self.company_id.id, False]),
                ("name", "=", self.name),
            ]
        )
        if pallet_record - self:
            raise ValidationError(_("Color Pallet name already exists!!"))

    @api.model_create_multi
    def create(self, vals_list):
        pallets = super().create(vals_list)
        for pallet in pallets:
            if (
                self._context.get("dark_color_pallet", False)
                and self.show_pallet_mode != "light"
            ):
                pallet.company_id.dark_colour_scheme_pallet_id = pallet.id
            else:
                pallet.company_id.colour_scheme_pallet_id = pallet.id

        return pallets
