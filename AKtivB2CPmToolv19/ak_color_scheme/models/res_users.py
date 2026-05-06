# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

    def set_user_color_scheme(self, scheme_id=False):
        """
        Set the user’s color scheme based on the current UI mode.

        This method assigns a color scheme pallet to the user.
        If the current UI mode (from cookies) is dark, the dark
        color scheme field is updated; otherwise, the light
        color scheme field is updated.

        :param int scheme_id: ID of the selected color scheme pallet
        :return: True if the update succeeds
        :rtype: bool
        """
        self.ensure_one()

        current_mode = request.httprequest.cookies.get("color_scheme")
        vals = {"colour_scheme_pallet_id": scheme_id or False}

        if current_mode == "dark":
            vals = {"dark_colour_scheme_pallet_id": scheme_id or False}

        self.sudo().write(vals)

        return True
