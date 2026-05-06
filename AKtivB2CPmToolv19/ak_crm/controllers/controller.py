# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class AktivPMSPortal(http.Controller):
    @http.route("/projects", type="http", auth="public", methods=["POST"], csrf=False)
    def webhook(self, **data):
        if request.method == "POST":
            return http.Response(status=200)
        else:
            return http.Response(status=400)
