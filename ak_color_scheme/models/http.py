# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import Response, request

def render(self):
    """
    Render the template with the appropriate company context.

    This method injects the current HTTP request into the template
    context and determines the active company based on the `cids`
    cookie. If a valid company ID is found, it is added to the
    rendering context as `active_id`.

    :return: Rendered template output
    :rtype: str
    """
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
        """
        Extend session information with color scheme configuration.

        This method enhances the default session data by adding available
        color scheme pallets, the currently selected light and dark schemes
        for the user, and company-level configuration that controls whether
        users can change their color scheme.

        The active company is determined from the `cids` cookie, and the
        visible color schemes are filtered based on the `color_scheme`
        cookie (light or dark mode).

        :return: Updated session information dictionary
        :rtype: dict
        :return:
        """
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
