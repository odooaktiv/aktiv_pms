# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software.
# See LICENSE file for full copyright & licensing details.

from odoo import models
from odoo.http import Response, request


def render(self):
    self.qcontext["request"] = request
    cids = request.httprequest.cookies.get("cids") or []
    if cids:
        cids = cids.split(",")
    try:
        self.qcontext["active_id"] = cids and request.env[
            "res.company"
        ].sudo().browse(int(cids[0]) or False)
    except Exception:
        pass
    return request.env["ir.ui.view"]._render_template(
        self.template, self.qcontext
    )


Response.render = render


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        session_info = super().session_info()
        user = self.env.user
        schemes = request.env["colour.scheme.pallet"].search([])
        color_scheme = request.httprequest.cookies.get("color_scheme")
        if not color_scheme or color_scheme == "light":
            schemes = schemes.filtered(
                lambda rec: rec.show_pallet_mode != "dark"
            )
        else:
            schemes = schemes.filtered(
                lambda rec: rec.show_pallet_mode != "light"
            )
        company = (
            request.env["res.company"]
            .sudo()
            .browse(
                request.httprequest.cookies.get("cids")
                and int(request.httprequest.cookies.get("cids").split(",")[0])
                or False
            )
        )
        session_info.update(
            {
                "color_scheme_pallets": {
                    "allow_user_color_scheme": company.allow_user_scheme,
                    "current_color_scheme": (
                        [
                            user.colour_scheme_pallet_id.id,
                            user.colour_scheme_pallet_id.name,
                        ]
                        if user.colour_scheme_pallet_id
                        else ""
                    ),
                    "current_color_scheme_dark": (
                        [
                            user.dark_colour_scheme_pallet_id.id,
                            user.dark_colour_scheme_pallet_id.name,
                        ]
                        if user.dark_colour_scheme_pallet_id
                        else ""
                    ),
                    "color_schemes": {
                        scheme.id: {
                            "id": scheme.id,
                            "name": scheme.name,
                        }
                        for scheme in schemes
                    },
                }
            }
        )
        return session_info
