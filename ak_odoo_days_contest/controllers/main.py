import json

from odoo import http
from odoo.http import request


class AktivOdooDays(http.Controller):
    @http.route(
        "/odoo/days/contest",
        type="http",
        auth="public",
        methods=["GET", "POST"],
        website=True,
        csrf=False,
        sitemap=False,
    )
    def odoo_days_contest(self, **kw):
        fields = ['name', 'email', 'mobile', 'participant_type', 'objectives']
        if request.httprequest.method == 'POST':
            if kw:
                # Get the objectives string, default to empty string if not provided
                objectives_str = kw.get("objectives", "").strip()
                
                # Initialize objectives as an empty list
                kw["objectives"] = []
                
                # Only attempt to load JSON if objectives_str is not empty
                if objectives_str:
                    try:
                        # Attempt to parse the JSON data
                        kw["objectives"] = json.loads(objectives_str)
                    except json.JSONDecodeError:
                        # Handle JSON decode error
                        kw["error"] = "Invalid JSON format for objectives!"
            if all(kw.get(field, False) for field in fields):
                participation = request.env["odoo.days.participant"].sudo().create({
                    "name": kw.get("name"),
                    "email": kw.get("email"),
                    "mobile": kw.get("mobile"),
                    "objectives": [int(objective) for objective in kw.get("objectives")],
                    "participant_type": int(kw.get("participant_type")),
                })
                survey = participation.participant_type.survey_id
                user_input = request.env["survey.user_input"].sudo().create({
                    "survey_id": survey.id,
                    "email": participation.email,
                    "participant_id": participation.id,
                    "user_input_line_ids": [(0, 0, {"question_id": q.id}) for q in survey.question_ids],
                })
                participation.answers = user_input.id
                return request.redirect(user_input.survey_id.sudo().get_start_url())
            else:
                kw["error"] = "Missing required values!"
        
        participant_type_options = request.env["participant.type"].sudo().search([])
        objective_options = request.env["odoo.days.objective"].sudo().search([])

        kw["participant_type_options"] = participant_type_options
        kw["objective_options"] = objective_options

        return request.render("ak_odoo_days_contest.ak_odoo_days_contest", kw)
