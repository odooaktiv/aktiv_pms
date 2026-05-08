import json

from odoo import http
from odoo.http import request


class AktivOdooDays(http.Controller):
    """
    Controller Aktiv Odoo Days exposes the public website endpoints
    used to render and process the Odoo Days contest registration
    form.

    The controller is responsible for rendering the registration
    page, validating user submissions, creating the participant
    record together with an associated survey user input, and
    finally redirecting the participant to the start of their
    assigned survey.
    """

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
        """Define: Odoo Days Contest Registration
        Route: /odoo/days/contest

        Renders the Odoo Days contest registration form on GET and
        processes the submitted data on POST.

        On POST, the method parses the JSON-encoded list of
        objectives from the form payload, validates that all
        required fields are present, and then:

        1. Creates a new `odoo.days.participant` record with the
           submitted name, email, mobile, objectives and participant
           type.
        2. Creates a new `survey.user_input` record for the survey
           that is linked to the selected participant type, pre
           populating one empty input line per survey question.
        3. Stores the created survey user input on the participant
           and redirects the visitor to the survey start URL.

        On GET (or when the submission is invalid), the method loads
        the available participant types and objectives and renders
        the `ak_odoo_days_contest.ak_odoo_days_contest` template,
        passing along any error message produced during validation.

        :param kw: Keyword arguments coming from the HTTP request,
            expected to contain `name`, `email`, `mobile`,
            `participant_type` and `objectives` on POST.
        :return: A redirect response to the survey start URL on a
            successful submission, otherwise a rendered response of
            the registration template.
        :raise: None
        """
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
