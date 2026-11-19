# -*- coding: utf-8 -*-
import logging
import mimetypes
import re

from markupsafe import Markup
from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AktivOutlookHooks(http.Controller):

    # kind -> (model, the address field the record keeps in its own right).
    # Both models also carry partner_id, which is the other place the sender's
    # address can be hiding once someone has tidied the record up.
    _RECORD_KINDS = {
        'lead': ('crm.lead', 'email_from'),
        'ticket': ('helpdesk.ticket', 'partner_email'),
    }

    # Inline images arrive as <img src="cid:...">. The add-in deliberately does
    # not upload inline parts (getRealAttachments filters on isInline), and
    # Office.js exposes no content-id on AttachmentDetails anyway, so there is
    # nothing on this side to repoint them at. Left in place they render as
    # broken-image icons in the chatter; dropping them is the honest option.
    _CID_IMG_RE = re.compile(r'<img\b[^>]*\bsrc=["\']cid:[^"\']*["\'][^>]*>', re.IGNORECASE)

    def _authenticate_outlook(self):
        """Run mail_plugin's outlook token check here, from inside the handler,
        instead of letting ``auth='outlook'`` run it at dispatch time.

        Odoo only attaches the CORS headers in ``Dispatcher.pre_dispatch``, and
        ``_serve_ir_http`` calls ``_authenticate()`` *before* ``_pre_dispatch()``
        (odoo/http.py). A rejected token therefore produces an error response
        carrying no ``Access-Control-Allow-Origin`` - and a cross-origin reply
        without that header is one the browser throws away without ever handing
        it to the page. The add-in's ``fetch`` then rejects with a bare
        TypeError, indistinguishable from the server being down, so an expired
        token surfaced as "couldn't reach that Odoo server, check the URL and
        CORS" and sent people off auditing healthy infrastructure.

        Authenticating in the handler keeps the whole reply on the ordinary
        dispatch path, headers included, so the add-in can actually read it and
        say "reconnect". ``_auth_method_outlook`` also does the
        ``request.update_env(user=...)``, so on success everything below runs as
        the API key's user exactly as it did under ``auth='outlook'``.
        """
        try:
            request.env['ir.http']._auth_method_outlook()
        except BadRequest:
            return False
        return True

    def _find_or_create_partner(self, email, name):
        if not email:
            return False
        partner = request.env['res.partner'].search([('email', '=', email)], limit=1)
        if not partner:
            partner = request.env['res.partner'].create({'name': name or email, 'email': email})
        return partner

    def _create_attachments(self, model, res_id, attachments):
        """Returns the ids created, so the chatter path can hand them to
        message_post and have them show up on the note itself rather than only
        in the record's Documents tab.
        """
        created = []
        for att in attachments or []:
            if not att.get('content'):
                continue
            name = att.get('name') or 'attachment'
            created.append(request.env['ir.attachment'].create({
                'name': name,
                'res_model': model,
                'res_id': res_id,
                # Office.js's getAttachmentContentAsync with format=Base64
                # already hands back base64 - ir.attachment.datas wants exactly that.
                'datas': att['content'],
                'mimetype': att.get('mimetype') or self._guess_mimetype(name),
            }).id)
        return created

    def _email_note_body(self, subject, name, email, body, direction='incoming'):
        """Build the chatter note for an email being filed onto a record.

        ``direction`` is which way the mail is travelling, because the address
        the add-in sends up means the opposite thing in each case. Reading a
        mail, the contact is whoever wrote to you. Composing one - which is
        every send-and-file - the contact is whoever you are writing *to*, so
        labelling it "From:" credits the customer with an email they are about
        to receive. The header has to say "Sent to:" there, or the note is a lie
        about who wrote the mail it is quoting.

        Two more things this has to get right:

        The chatter credits the API key's user as the author, so with no header
        the note reads as though an internal user sat down and typed the
        customer's email out. Leading with the subject and the real sender puts
        it back in context for whoever reads the record later.

        And the body must be Markup. ``message_post`` escapes a plain ``str``
        ("str content will be escaped, Markup for html body" - its own
        docstring), which is what rendered the first version of this note as a
        wall of visible HTML source instead of the email. Markup is safe here
        because ``mail.message.body`` is ``fields.Html(sanitize_style=True)``
        and Html fields sanitize on write by default, so scripts and unsafe
        attributes are stripped whatever the sender put in the mail.
        """
        who = '%s <%s>' % (name, email) if name and email else (email or name or '')

        header_bits = []
        if subject:
            header_bits.append(Markup('<div style="font-weight:600;">%s</div>') % subject)
        if who:
            label = 'Sent to' if direction == 'outgoing' else 'From'
            # Markup's % escapes what it interpolates, so a display name with an
            # angle bracket or an ampersand in it cannot break out into markup.
            header_bits.append(
                Markup('<div style="color:#6c757d;font-size:12px;">%s: %s</div>') % (label, who))

        header = Markup('')
        if header_bits:
            header = Markup(
                '<div style="margin:0 0 10px;padding:0 0 8px;'
                'border-bottom:1px solid #e0e0e0;">%s</div>'
            ) % Markup('').join(header_bits)

        return header + Markup(self._CID_IMG_RE.sub('', body or ''))

    def _guess_mimetype(self, name):
        """Office.js only reports a content type for attachments on a message
        being read; AttachmentDetailsCompose (a draft, i.e. the add-in's compose
        panel) has no contentType field at all. Falling straight through to
        octet-stream there would leave every file created from a draft
        undisplayable in Odoo - no inline preview, download only - so guess from
        the filename before giving up.
        """
        return mimetypes.guess_type(name)[0] or 'application/octet-stream'

    @http.route('/aktiv/lead/create', type='jsonrpc', auth='none', cors='*')
    def create_lead(self, subject, email=None, name=None, body='', attachments=None,
                    lead_type='lead', **kw):
        # Must stay the first statement: auth='none' means nothing has checked
        # the caller yet. See _authenticate_outlook for why the check lives here
        # rather than in the route's auth=.
        if not self._authenticate_outlook():
            return {'error': 'TOKEN_REJECTED'}

        # Lead and opportunity are the same model with a different `type`.
        # Anything else falls back to a lead, which is what older add-in builds
        # (that never send lead_type) have always created.
        if lead_type not in ('lead', 'opportunity'):
            lead_type = 'lead'

        partner = self._find_or_create_partner(email, name)
        # An opportunity picks up the API key's user as salesperson, their
        # team, and the first unfolded stage from crm.lead's own defaults and
        # computes, so it lands in the pipeline the same way one made in Odoo does.
        lead = request.env['crm.lead'].create({
            'type': lead_type,
            'name': subject,
            'partner_id': partner.id if partner else False,
            'contact_name': name,
            'email_from': email,
            'description': body,
        })
        self._create_attachments('crm.lead', lead.id, attachments)
        return {'id': lead.id}

    @http.route('/aktiv/helpdesk/create', type='jsonrpc', auth='none', cors='*')
    def create_ticket(self, subject, email=None, name=None, body='', attachments=None, **kw):
        # Must stay the first statement - see create_lead.
        if not self._authenticate_outlook():
            return {'error': 'TOKEN_REJECTED'}

        partner = self._find_or_create_partner(email, name)
        ticket = request.env['helpdesk.ticket'].create({
            'name': subject,
            'partner_id': partner.id if partner else False,
            'partner_name': name,
            'partner_email': email,
            'description': body,
        })
        self._create_attachments('helpdesk.ticket', ticket.id, attachments)
        return {'id': ticket.id}

    def _aktiv_name_search_domain(self, model, query):
        """Match ``query`` against whatever a person actually reads in the
        list: the record's own title and the name of whoever it is for."""
        if model == 'crm.lead':
            return ['|', '|',
                    ('name', 'ilike', query),
                    ('partner_id.name', 'ilike', query),
                    ('contact_name', 'ilike', query)]
        return ['|', ('name', 'ilike', query), ('partner_name', 'ilike', query)]

    def _aktiv_search_crm_leads(self, domain, limit):
        """Open opportunities first, then leads.

        An opportunity already in progress is usually exactly what someone
        typing a customer's name into this picker is looking for, and it is
        the easiest thing to bury under a pile of fresh, unqualified leads if
        the two are just interleaved by date. Wins are excluded outright
        rather than sorted last: action_set_won always leaves probability at
        100, so that one condition catches a win regardless of which stage a
        pipeline uses for it, and a customer whose deal already closed is not
        who this picker is for. Losses need no filter of their own - marking
        a lead lost sets active to False, which search() already excludes by
        default.
        """
        Lead = request.env['crm.lead']
        opportunities = Lead.search(
            domain + [('type', '=', 'opportunity'), ('probability', '<', 100)],
            order='write_date desc', limit=limit)
        remaining = limit - len(opportunities)
        if remaining <= 0:
            return opportunities
        leads = Lead.search(
            domain + [('type', '=', 'lead')],
            order='write_date desc', limit=remaining)
        return opportunities + leads

    @http.route('/aktiv/record/search', type='jsonrpc', auth='none', cors='*')
    def search_records(self, kind, email=None, query=None, limit=8, **kw):
        """Candidate records to file the open email against.

        Runs as the API key's user, so record rules decide what comes back -
        someone only sees the leads or tickets they could already open in Odoo.
        """
        # Must stay the first statement - see create_lead.
        if not self._authenticate_outlook():
            return {'error': 'TOKEN_REJECTED'}

        spec = self._RECORD_KINDS.get(kind)
        if not spec:
            return {'error': 'Unknown record type.'}
        model, email_field = spec
        limit = max(1, min(int(limit or 8), 20))
        query = (query or '').strip()

        # A typed name beats an address match once someone bothers to type
        # one - it is the only way a compose draft with no recipient yet can
        # find anything at all, and it is faster than scanning an
        # address-matched list on a reply too. The sender's address is the
        # next best anchor: match the address the record carries itself or
        # the one on its linked partner, since filing an email usually means
        # the partner is already set. With neither, fall back to whatever was
        # touched last, which beats an empty list.
        if query:
            domain = self._aktiv_name_search_domain(model, query)
        elif email:
            domain = ['|', (email_field, '=ilike', email), ('partner_id.email', '=ilike', email)]
        else:
            domain = []

        if model == 'crm.lead':
            records = self._aktiv_search_crm_leads(domain, limit)
        else:
            records = request.env[model].search(domain, order='write_date desc', limit=limit)

        return {'records': [{
            'id': record.id,
            'name': record.display_name,
            # Stage is what tells two same-named records apart in the list.
            'stage': record.stage_id.name if record.stage_id else '',
            # crm.lead is both halves of the pipeline - a lead and an
            # opportunity are the same model with a different `type`. The picker
            # says "lead" for the whole list, so without this an opportunity
            # (which is what people filing a quote are actually looking for)
            # reads as a lead and gets skipped over. Blank for helpdesk, where
            # there is only one kind of thing to find.
            'kind_label': dict(
                lead='Lead', opportunity='Opportunity',
            ).get(record.type, '') if model == 'crm.lead' else '',
        } for record in records]}

    @http.route('/aktiv/record/append', type='jsonrpc', auth='none', cors='*')
    def append_to_record(self, kind, id, subject=None, email=None, name=None,
                         body='', attachments=None, direction='incoming', **kw):
        """File the open email onto an existing lead or ticket as a chatter note.

        ``direction`` is 'incoming' for a mail being read and 'outgoing' for a
        draft - which is what the add-in's send-and-file button posts, just
        before it hands the draft to Outlook to send. It only changes the note's
        header wording; see _email_note_body. It defaults to 'incoming' so an
        add-in older than the send-and-file build keeps its existing behaviour.
        """
        # Must stay the first statement - see create_lead.
        if not self._authenticate_outlook():
            return {'error': 'TOKEN_REJECTED'}

        spec = self._RECORD_KINDS.get(kind)
        if not spec:
            return {'error': 'Unknown record type.'}
        model = spec[0]

        # browse().exists() rather than a bare browse: the picker list the
        # add-in is working from can be minutes old by the time someone clicks.
        record = request.env[model].browse(int(id)).exists()
        if not record:
            return {'error': 'That record no longer exists.'}

        attachment_ids = self._create_attachments(model, record.id, attachments)

        # mail.mt_note, not the default comment subtype. This is filing a copy
        # of an email onto the record for whoever picks it up next - posting it
        # as a comment would mail it out to every follower, which is not what
        # "add this to the ticket" is ever meant to do.
        record.message_post(
            subject=subject or False,
            body=self._email_note_body(subject, name, email, body, direction),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
            attachment_ids=attachment_ids,
        )
        _logger.info('Aktiv Outlook - appended %s email to %s#%s',
                     direction, model, record.id)
        return {'id': record.id, 'name': record.display_name}
