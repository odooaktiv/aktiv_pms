# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software.
# See LICENSE file for full copyright & licensing details.

from odoo import models, fields
from odoo.http import request


class ResUsers(models.Model):
    _inherit = "res.users"

    colour_scheme_pallet_id = fields.Many2one(
        "colour.scheme.pallet", "Color Scheme"
    )
    dark_colour_scheme_pallet_id = fields.Many2one(
        "colour.scheme.pallet", "Dark Color Scheme"
    )

    def set_user_color_scheme(self, scheme):
        current_mode = request.httprequest.cookies.get("color_scheme")
        vals = {"colour_scheme_pallet_id": scheme or False}
        if current_mode == "dark":
            vals = {"dark_colour_scheme_pallet_id": scheme or False}
        return self.sudo().write(vals)
