""" Aktiv Customer Portal"""
from odoo import _, http  # pylint: disable=E0401
from odoo.addons.auth_signup.controllers.main import \
    AuthSignupHome  # pylint: disable=E0401
from odoo.addons.website.controllers.main import \
    Website  # pylint: disable=E0401
from odoo.exceptions import UserError  # pylint: disable=E0401
from odoo.http import request


class ResetPassword(AuthSignupHome):

    """AuthSignupHome Reset Password"""

    def _prepare_signup_values(self, qcontext):
        res = super(ResetPassword, self)._prepare_signup_values(qcontext)
        values = {key: qcontext.get(key) for key in ("login", "name", "password")}
        if values:
            if len(values.get("password")) < 8:
                raise UserError(_("Password length must be eight characters."))
        return res


class Website(Website):

    """Website"""
    @http.route('/', auth="public", website=True, sitemap=True)
    def index(self, **kw):
        """Override to return signin page as homepage"""
        # prefetch all menus (it will prefetch website.page too)
        top_menu = request.website.menu_id

        homepage_url = request.website._get_cached('homepage_url')
        if homepage_url and homepage_url != '/':
            request.env['ir.http'].reroute(homepage_url)

        # Check for page
        # _serve_page() in V19 raises IndexError when response body is empty
        website_page = None
        try:
            website_page = request.env['ir.http']._serve_page()
        except IndexError:
            pass

        if website_page is not None:
            # Customization Starts
            if not request.session.uid:
                return request.redirect("/web/login")
            return request.redirect("/my/home")
            # Customization Ends

        # Check for controller
        if homepage_url and homepage_url != '/':
            try:
                return request._serve_ir_http()
            except Exception:
                pass

        # Fallback on first accessible menu
        def is_reachable(menu):
            return menu.is_visible and menu.url not in ('/', '', '#') and not menu.url.startswith(('/?', '/#', ' '))

        reachable_menus = top_menu.child_id.filtered(is_reachable)
        if reachable_menus:
            return request.redirect(reachable_menus[0].url)

        raise request.not_found()
