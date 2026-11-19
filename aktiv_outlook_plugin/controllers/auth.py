# -*- coding: utf-8 -*-
import datetime
import logging

from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request

_logger = logging.getLogger(__name__)


class AktivOutlookAuth(http.Controller):

    # Config parameter holding the origins allowed to call the login route,
    # comma separated, e.g. "https://portal.aktivsoftware.com".
    ALLOWED_ORIGINS_PARAM = 'aktiv_outlook_plugin.allowed_origins'

    def _origin_allowed(self):
        """Whether the calling page may log in, and the header to answer with.

        This route is the one that takes a PASSWORD and hands back a working
        API key, so unlike the token-protected routes it must not be callable
        by every website on the internet. `cors='*'` stays on the decorator --
        Odoo answers the preflight out of that static routing dict in
        pre_dispatch, before any handler runs, and dropping it there would
        break the preflight entirely -- so the restriction is applied here
        instead: the actual response carries only the matched origin, and a
        caller from anywhere else is refused before any credential is checked.
        Refusing early matters as much as the header: it keeps an unknown site
        from using this endpoint to guess passwords, which it could otherwise
        do blind even without being able to read the reply.

        An unset parameter keeps today's behaviour rather than locking every
        deployment out on upgrade, but says so in the log every time.
        """
        origins = request.env['ir.config_parameter'].sudo().get_param(
            self.ALLOWED_ORIGINS_PARAM, '')
        allowed = [o.strip().rstrip('/') for o in origins.split(',') if o.strip()]
        origin = (request.httprequest.headers.get('Origin') or '').rstrip('/')

        if not allowed:
            _logger.warning(
                'Aktiv Outlook login is accepting any origin. Set the %s system '
                'parameter to the add-in origin to close this.',
                self.ALLOWED_ORIGINS_PARAM)
            return True

        if origin and origin in allowed:
            # Echo the one origin rather than '*', so only the add-in can read
            # the minted key.
            request.future_response.headers.set(
                'Access-Control-Allow-Origin', origin)
            request.future_response.headers.set('Vary', 'Origin')
            return True

        _logger.warning(
            'Aktiv Outlook login refused for origin %r; allowed: %s',
            origin or '<none>', ', '.join(allowed))
        return False

    @http.route('/aktiv/auth/login', type='jsonrpc', auth='none', cors='*', methods=['POST', 'OPTIONS'])
    def login(self, login=None, password=None, db=None, **kw):
        """Direct username/password (or API key) login, replacing mail_plugin's
        OAuth popup/consent dialog with a plain form. On success this mints the
        same odoo.plugin.outlook scoped API key that dialog flow produces, so
        auth_method_outlook (mail_plugin/models/ir_http.py) validates it exactly
        the same way on every other route.

        Odoo 19 notes:

        * The credential is checked with ``res.users.authenticate`` directly
          rather than ``request.session.authenticate``: the add-in only needs the
          scoped key, not a browser session cookie, and the session API changed
          signature in 18.0 (``authenticate(env, credential)``).
        * The password field also accepts a personal API key (Odoo: Preferences >
          Account Security > New API Key). That is the only way in for a user who
          has two-factor authentication enabled: a plain password is refused for
          them, because this route cannot run the TOTP step.
        * ``res.users.apikeys._generate`` now takes an expiration date. We use the
          same ``mail_plugin.access_token_expiration_days`` parameter (default 30)
          as Odoo's own Outlook connect dialog.
        """
        if not self._origin_allowed():
            return {'error': 'This add-in is not authorised to sign in to this '
                             'server. Contact your administrator.'}

        if not login or not password:
            return {'error': 'Username and password are required.'}

        if db and db != request.db:
            # One database per domain: a mismatch means a wrong database name
            # was typed, not a real multi-db setup we need to support.
            return {'error': 'Wrong database name for this server.'}

        Users = request.env['res.users'].sudo()
        uid = False

        # 1. A personal API key pasted into the password field (global scope).
        key_uid = request.env['res.users.apikeys'].sudo()._check_credentials(
            scope='rpc', key=password)
        if key_uid:
            key_user = Users.browse(key_uid)
            if key_user.active and key_user.login == login:
                uid = key_uid

        # 2. A regular password.
        if not uid:
            credential = {'login': login, 'password': password, 'type': 'password'}
            try:
                auth_info = request.env['res.users'].authenticate(
                    credential, {'interactive': True})
            except AccessDenied:
                return {'error': 'Invalid username or password.'}
            uid = auth_info['uid']
            if auth_info.get('mfa') != 'skip' and Users.browse(uid)._mfa_url():
                return {'error': 'This account uses two-factor authentication. '
                                 'Create an API key in Odoo (Preferences > Account '
                                 'Security) and paste it in the password field.'}

        request.update_env(user=uid)
        if not request.env.user._is_internal():
            return {'error': 'Only internal users can connect this add-in.'}

        expiration_days = int(request.env['ir.config_parameter'].sudo().get_param(
            'mail_plugin.access_token_expiration_days', 30) or 30)
        if expiration_days <= 0:
            expiration_days = 30
        # sudo() keeps env.user, so the key belongs to the authenticated user;
        # sudo only lifts the per-group maximum key duration, as mail_plugin does.
        api_key = request.env['res.users.apikeys'].sudo()._generate(
            'odoo.plugin.outlook', 'Aktiv for Outlook',
            datetime.datetime.now() + datetime.timedelta(days=expiration_days))
        _logger.info('Aktiv Outlook direct login - user %s', request.env.user.login)
        return {'access_token': api_key}
