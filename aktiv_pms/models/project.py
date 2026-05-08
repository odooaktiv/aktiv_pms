# -*- coding: utf-8 -*-

from collections import defaultdict

import pytz
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from ..utils import get_connection



class Project(models.Model):
    _inherit = "project.project"

    deployment_type = fields.Selection([
        ("task_wise", "Task Wise"),
        ("phase_wise", "Phase Wise"),
    ])
    go_live_date = fields.Date()

    display_testcases = fields.Boolean(default=True, help="If checked, display task testcases on portal")

    development_hours = fields.Float(
        string="Development hours",
        compute="_compute_development_hours",
    )

    consulting_hours = fields.Float(
        string="Consulting hours",
        compute="_compute_consulting_hours",
    )

    total_planned_hours = fields.Float(
        string="Task Planned Hours",
        compute="_compute_planned_total_hours",
        default=0,
    )
    developer_ids = fields.Many2many(
        "res.users",
        "project_developer_rel",
        "project_id",
        "user_id",
        string="Developer",
        tracking=True,
    )
    task_qa_ids = fields.Many2many(
        "res.users",
        "project_qa_rel",
        "project_id",
        "user_id",
        string="QA",
        tracking=True,
    )
    code_reviewer_ids = fields.Many2many(
        "res.users",
        "project_cr_rel",
        "project_id",
        "user_id",
        string="Code Reviewer",
        tracking=True,
    )
    team_leader_ids = fields.Many2many(
        "res.users",
        "project_tl_rel",
        "project_id",
        "user_id",
        domain=lambda self: [("group_ids", "=", self.env.ref("aktiv_pms.group_aktiv_project_team_leader").id)],
        string="Lead Engineer",
        tracking=True,
    )
    consultant_ids = fields.Many2many(
        "res.users",
        "project_consult_rel",
        "project_id",
        "user_id",
        string="Consultant",
        tracking=True,
    )
    is_project_create = fields.Boolean('Is Project Create', copy=False)
    basic_info_doc = fields.Binary(string="Basic Customer Info")
    basic_info_filename = fields.Char("Basic Info File Name")
    migration_doc = fields.Binary(string="Data Migration Template")
    migration_filename = fields.Char("Data Migration File Name")
    communication_tool_id = fields.Many2many(
        "communication.tool", string="Communication Plan/Tool"
    )
    frequency = fields.Selection(
        [
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("byweekly", "By-Weekly"),
            ("monthly", "Monthly"),
        ]
    )
    generate_meeting_frequency = fields.Selection(
        [("weeks", "Weeks"), ("months", "Months")]
    )
    generate_meeting_from = fields.Datetime("Generate Meeting From")
    meeting_line = fields.One2many(
        "aktiv.meeting", "project_id", "Meetings", tracking=True
    )
    month_weekdays_ids = fields.Many2many("month.weekday", string="Weekday")
    month_dates_id = fields.Many2one("month.date", string="Month Date")
    generate_meeting_until = fields.Integer(string="Generate Meeting Until")
    customization_task_count = fields.Integer(
        compute="_compute_task_count_based_on_type", string="Customization Task Count"
    )
    approved_hour_task_count = fields.Integer(
        compute="compute_approved_hour_task_count"
    )
    consulting_task_count = fields.Integer(
        compute="_compute_task_count_based_on_type", string="Consulting Task Count"
    )
    init_hours = fields.Float(
        string="Approved Hours", compute="_compute_total_planned_hours"
    )
    support_pack_lines = fields.One2many("support.pack", "project_id")
    timesheet_approved_hours = fields.Float(
        string="Timesheet Approved Hours", default=0
    )
    total_timesheet_time = fields.Float(
        compute="_compute_total_timesheet_time",
        groups="hr_timesheet.group_hr_timesheet_user",
        help="Total number of time (in the proper UoM) recorded in the project, rounded to the unit.",
    )
    project_owner_ids = fields.Many2many("res.users", string="Project Lead")
    version = fields.Float(string="Version")
    customer_success_manager_id = fields.Many2one(
        "res.users",
        string="Customer Success Manager"
    )
    allow_effective_as_invested_hours = fields.Boolean(help="Allow Effective same as Invested", string="Allow Effective same as Invested")
    # portal_customer_task_count = fields.Integer(string="Portal Customer Task Count",
    #                                             compute="_compute_portal_customer_task_count")

    # Added field for Credentials page
    url = fields.Char(string="URL")
    username = fields.Char(string="User Name")
    password = fields.Char(string="Password")
    commit_token = fields.Char(string="Commit Token")
    customer_project = fields.Boolean('Is Customer Project?')
    pm_tool_project_id = fields.Char(string='PM Tool Project ID')
    pm_tool_task_id = fields.Char(string='PM Tool Task ID')
    pm_tool_task_name = fields.Char(string='PM Tool Task Name')

    def _get_customization_task_ids(self, project_id):
        """return customization (task type) types of task"""
        task_ids = project_id.sudo().task_ids.filtered(
            lambda l: not l.parent_id
            and (l.approved_hours > 0 or l.productive_hours_on_sub_task > 0)
        )
        return task_ids

    def _get_task_stages(self, projects):
        # Get task IDs
        customization_task_ids = self._get_customization_task_ids(projects)

        # Define state mappings
        state_mappings = {
            "development": ["dev", "call_consult", "cd_review", "qa", "redevelop"],
            "customer_review": ["cust_review"],
            "done": ["done", "cancel"],
            "new": ["new"],
        }

        # Count tasks in different states
        task_states = {
            state: [task for task in customization_task_ids if task.state in states_list]
            for state, states_list in state_mappings.items()
        }
        return task_states

    def sync_project(self):
        """This method used for call the Wizard for creation of B2C project."""
        return {
            "name": "Create Project PMS",
            "type": "ir.actions.act_window",
            "res_model": "project.creation.wizard",
            "view_mode": "form",
            "view_type": "form",
            "context": {
                "default_name": self.name,
                "default_partner_id": self.partner_id.id,
                "default_task": self.name + ' -  General Task'
            },
            "target": "new",
        }

    def _get_consult_task_ids(self, project_id):
        """return consult (task type) types of task"""
        task_ids = project_id.sudo().task_ids.filtered(
            lambda l: l.task_type_id.id in [self.env.ref('aktiv_pms.task_type_consulting').id, self.env.ref('aktiv_pms.task_type_communication').id]
            and not l.parent_id
            and l.state == "call_consult"
            and (l.approved_hours > 0 or l.is_visible_dashboard)
        )
        return task_ids

    @api.onchange("generate_meeting_from")
    def _onchange_generate_meeting_from(self):
        if (
            self.generate_meeting_from and self.date_start
            and self.generate_meeting_from.date() < self.date_start
        ):
            raise ValidationError(
                _("Please select generate meeting date greater than start date!")
            )

    def _compute_development_hours(self):
        """store approved hours of development(customization) type tasks of
        current project in development_hours field"""
        for project in self:
            development_hours = sum(
                self.env["project.task"]
                .search(
                    [
                        ("project_id", "=", project.id),
                        ("task_type_id", "=", self.env.ref('aktiv_pms.task_type_customization').id),
                    ]
                )
                .mapped("approved_hours")
            )
            project.development_hours = development_hours or False

    def _compute_consulting_hours(self):
        """store approved hours of consulting type tasks of current project in
        consulting_hours field"""
        for project in self:
            consulting_hours = sum(
                self.env["project.task"]
                .search(
                    [
                        ("project_id", "=", project.id),
                        ("task_type_id", "=", self.env.ref('aktiv_pms.task_type_consulting').id),
                    ]
                )
                .mapped("approved_hours")
            )
            project.consulting_hours = consulting_hours or False

    @api.onchange("date_start")
    def _onchange_date_start(self):
        """Method to call when there is change in the start Date"""
        if self.date_start:
            if (
                self.generate_meeting_from
                and self.generate_meeting_from.date() < self.date_start
            ):
                self.generate_meeting_from = False

    @api.depends("support_pack_lines")
    def _compute_total_planned_hours(self):
        for project in self:
            project.init_hours = sum(project.support_pack_lines.mapped("planned_hours"))

    def _compute_remaining_hours(self):
        """Method to calculate remaining hours from initial hours"""
        # Let the parent assign effective_hours and is_project_overtime (v19 requirement).
        super()._compute_remaining_hours()
        self.timesheet_approved_hours = 0.0
        for project in self:
            for task in project.tasks:
                project.timesheet_approved_hours += task.approved_hours
            project.remaining_hours = (
                project.init_hours - project.timesheet_approved_hours
            )

    def _compute_planned_total_hours(self):
        """Method to compute the total planned hours in project."""
        group_read = self.env["project.task"].read_group(
            domain=[
                ("planned_hours", "!=", False),
                ("project_id", "in", self.filtered("allow_timesheets").ids),
            ],
            fields=["planned_hours:sum"],
            groupby="project_id",
        )
        group_per_project_id = {
            group["project_id"][0]: group["planned_hours"] for group in group_read
        }
        for project in self:
            project.total_planned_hours = group_per_project_id.get(project.id)

    def _compute_task_count_based_on_type(self):
        """Method to compute the total tasks in project based on its types."""
        for project in self:
            task_ids = project.task_ids
            project.customization_task_count = len(
                task_ids.filtered(lambda p: p.task_type_id.id == self.env.ref('aktiv_pms.task_type_customization').id)
            )
            project.consulting_task_count = len(
                task_ids.filtered(lambda p: p.task_type_id.id == self.env.ref('aktiv_pms.task_type_consulting').id)
            )

    def compute_approved_hour_task_count(self):
        """Method used for count approved hours task"""
        for rec in self:
            rec.approved_hour_task_count = len(
                rec.task_ids.filtered(lambda task_count: task_count.approved_hours)
            )

    def default_get(self, fields):
        """To set the default values"""
        result = super(Project, self).default_get(fields)
        result["privacy_visibility"] = "followers"
        return result

    def get_meeting_end_date(self):
        end_date = False
        if self.generate_meeting_from and self.generate_meeting_until:
            if self.generate_meeting_frequency == "weeks":
                end_date = self.generate_meeting_from + relativedelta(
                    weeks=self.generate_meeting_until
                )
            elif self.generate_meeting_frequency == "months":
                end_date = self.generate_meeting_from + relativedelta(
                    months=self.generate_meeting_until
                )
        customer_tz = (
            self.partner_id.tz
            and pytz.timezone(self.partner_id.tz)
            or pytz.timezone("UTC")
        )
        user_tz = (
            self.env.user.tz and pytz.timezone(self.env.user.tz) or pytz.timezone("UTC")
        )
        return end_date, customer_tz, user_tz

    def get_cust_date(self, start_date, user_tz, customer_tz):
        # start datetime convert in user TZ
        user_time = pytz.utc.localize(start_date).astimezone(user_tz)
        # start datetime convert in customer TZ
        customer_time = pytz.utc.localize(start_date).astimezone(customer_tz)
        # get naive time to get actual timedelta as with aware dates the
        # delta is based on UTC
        user_time_naive = user_time.replace(tzinfo=None)
        customer_time_naive = customer_time.replace(tzinfo=None)
        # timedelta between user and cust timezone
        naive_diff = user_time_naive - customer_time_naive
        customer_date = start_date - naive_diff
        return customer_date

    def action_generate_meetings(self):
        end_date, customer_tz, user_tz = self.get_meeting_end_date()
        if end_date:
            invalid_meetings = self.meeting_line.filtered(
                lambda line: line.state != "completed"
            )

            invalid_meetings.with_context(
                {"for_generate": self.env.context.get("for_generate", False)}
            ).unlink()
            start_date = self.generate_meeting_from
            self.create_meeting_recs(start_date, end_date, customer_tz, user_tz)

    def create_meeting_recs(self, start_date, end_date, customer_tz, user_tz):
        added_weekdays = []
        week_day = [month_weeks for month_weeks in self.month_weekdays_ids.ids]
        while start_date <= end_date:
            customer_date = self.get_cust_date(start_date, user_tz, customer_tz)
            weekday = start_date.isoweekday()
            meeting_line = {
                "local_datetime": start_date,
                "cust_datetime": customer_date,
                "owner_ids": self.env.user,
            }
            # create meeting line for daily (Exclude weekend)
            if weekday <= 5 and self.frequency == "daily":
                self.meeting_line = [(0, 0, meeting_line)]

            # create meeting line for weekly (Exclude weekend)
            self.check_and_create_weekly(weekday, week_day, meeting_line)

            # create meeting line for byweekly (Exclude weekend)
            if weekday in week_day and self.frequency == "byweekly":
                # keep track of added weekdays to exclude in next week
                if weekday in added_weekdays:
                    added_weekdays.remove(weekday)
                else:
                    added_weekdays.append(weekday)
                    self.meeting_line = [(0, 0, meeting_line)]

            # create meeting line for monthly (Exclude weekend)
            self.check_and_create_monthly(
                start_date, customer_date, weekday, meeting_line
            )
            start_date += relativedelta(days=1)

    def check_and_create_weekly(self, weekday, week_day, meeting_line):
        if weekday in week_day and self.frequency == "weekly":
            self.meeting_line = [(0, 0, meeting_line)]

    def check_and_create_monthly(
        self, start_date, customer_date, weekday, meeting_line
    ):
        if self.frequency == "monthly" and start_date.day == self.month_dates_id.value:
            delta = relativedelta(days=0)
            # shift meeting to next weekday if it is on weekend
            if weekday == 6:
                delta = relativedelta(days=2)
            elif weekday == 7:
                delta = relativedelta(days=1)
            meeting_line["local_datetime"] = start_date + delta
            meeting_line["cust_datetime"] = customer_date + delta
            self.meeting_line = [(0, 0, meeting_line)]

    # noinspection PyInterpreter
    def _send_customer_review_mail(self):
        """Send Customer Project Review Mail."""
        # In v19, rating_active/rating_status moved from project.project to project.task.type;
        # use show_ratings (computed True when any stage has rating_active=True) as the filter.
        projects = self.search(
            [
                ("show_ratings", "=", True),
            ]
        )
        template_id = self.env.ref(
            "aktiv_pms.aktiv_review_project_request_email_template"
        ).id
        template = self.env["mail.template"].browse(template_id)
        for project in projects:
            email_values = {
                "email_to": project.partner_id.email,
            }
            template.send_mail(project.id, email_values=email_values, force_send=True)

    def action_open_tasks_based_on_type(self):
        self.ensure_one()
        action = {
            "name": _("Tasks"),
            "res_model": "project.task",
            "type": "ir.actions.act_window",
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }
        if self._context.get("display_only_customization_task"):
            action["domain"].append(
                ("task_type_id", "=", self.env.ref('aktiv_pms.task_type_customization').id),
            )
            action["context"].update(
                {
                    "default_task_type_id": self.env.ref('aktiv_pms.task_type_customization').id,
                }
            )
            if self.customization_task_count == 1:
                action["view_mode"] = "form"
                action["res_id"] = self.task_ids.filtered(
                    lambda l: l.task_type_id.id == self.env.ref('aktiv_pms.task_type_customization').id
                ).id
            else:
                action["view_mode"] = "tree,form,kanban,calendar,pivot,graph,activity"
        if self._context.get("display_only_consulting_task"):
            action["domain"].append(
                ("task_type_id", "=", self.env.ref('aktiv_pms.task_type_consulting').id),
            )
            action["context"].update(
                {
                    "default_task_type_id": self.env.ref('aktiv_pms.task_type_consulting').id,
                }
            )
            if self.consulting_task_count == 1:
                action["view_mode"] = "form"
                action["res_id"] = self.task_ids.filtered(
                    lambda l: l.task_type_id.id == self.env.ref('aktiv_pms.task_type_consulting').id
                ).id
            else:
                action["view_mode"] = "tree,form,kanban,calendar,pivot,graph,activity"
        return action

    @api.depends("timesheet_ids")
    def _compute_total_timesheet_time(self):
        # In v19, uom.uom.factor is the absolute conversion factor (e.g. days=8, hours=1).
        # To convert to reference unit: unit_amount * source.factor
        # To convert reference to encode UoM: total /= encode_uom.factor
        timesheets_read_group = self.env["account.analytic.line"]._read_group(
            [("project_id", "in", self.ids)],
            ["project_id", "product_uom_id"],
            ["unit_amount:sum"],
        )
        timesheet_time_dict = defaultdict(list)
        for project, product_uom, unit_amount_sum in timesheets_read_group:
            timesheet_time_dict[project.id].append((product_uom, unit_amount_sum))

        for project in self:
            total_time = 0.0
            for product_uom, unit_amount in timesheet_time_dict[project.id]:
                factor = (product_uom or project.timesheet_encode_uom_id).factor
                total_time += unit_amount * (1.0 if project.encode_uom_in_days else factor)
            # Convert from reference unit to the encode UoM set in settings
            total_time /= project.timesheet_encode_uom_id.factor
            project.total_timesheet_time = total_time

    # @api.depends("task_ids")
    # def _compute_portal_customer_task_count(self):
    #     for rec in self:
    #         rec.portal_customer_task_count = 0
    #         if rec.task_ids:
    #             rec.portal_customer_task_count = len(rec.task_ids.filtered(lambda l: (l.state == "new" and l.task_type == "customization") or ((l.approved_hours > 0 or l.is_visible_dashboard) and ((
    #                     l.task_type == "customization" and l.state in ["dev", "cust_review",
    #                                                                    "done"]) or (l.task_type in ["consulting",
    #                                                                                                 "communication"]
    #                                                                                 and l.state == "call_consult")))))

    def action_update_subtasks_states(self):
        context = self.env.context
        active_ids = context.get('active_ids')
        if active_ids:
            projects = self.env['project.project'].search([('id', 'in', active_ids)])
            for project in projects:
                done_cancelled_tasks = project.task_ids.filtered(lambda task: task.state in ('done', 'cancel'))
                for parent_task in done_cancelled_tasks:
                    tasks_to_update = parent_task.mapped('child_ids').filtered(lambda task: task.state not in ('done', 'cancel'))
                    if tasks_to_update:
                        tasks_to_update.write({'state': parent_task.state})

    def get_b2b_users(self,odoo_conn):
        """ To get b2b users for assigning as team members """
        for rec in self:
            b2c_project_user = rec.user_id.user_name
            b2c_tech_lead_user = rec.team_leader_ids.mapped('user_name')
            b2c_project_owner = rec.project_owner_ids.mapped('user_name')
            b2c_customer_success_manager = rec.customer_success_manager_id.user_name
            b2c_project_developers = rec.developer_ids.mapped('user_name')
            b2c_project_code_reviewers = rec.code_reviewer_ids.mapped('user_name')
            b2c_project_task_qa = rec.task_qa_ids.mapped('user_name')
            b2c_project_consultants = rec.consultant_ids.mapped('user_name')

            user_logins = ([b2c_project_user] + b2c_tech_lead_user + b2c_project_owner + [b2c_customer_success_manager] +
                           b2c_project_developers + b2c_project_code_reviewers + b2c_project_task_qa + b2c_project_consultants)
            users = odoo_conn.env['res.users'].search([('login', 'in', user_logins)])
        return users

    def update_b2b_team_members(self):
        """ update b2b tema members if any stakeholders are updated in b2c """
        try:
            odoo_conn = get_connection(self.env)
        except Exception as e:
            raise ValidationError(e)
        if not odoo_conn:
            raise ValidationError("Please establish connection with database!")
        for rec in self:
            users = rec.get_b2b_users(odoo_conn)
            team_member_ids = [odoo_conn.env.uid]
            team_member_ids.extend(users)
            b2b_project_id = odoo_conn.env['project.project'].browse([int(rec.pm_tool_project_id)])
            b2b_project_id.write({'team_member_ids': [(6, 0, team_member_ids)]})

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override read_group to filter out archived users in grouping"""
        result = super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)

        # Fields that should filter out archived users
        user_fields_to_filter = ['team_leader_ids', 'user_id']

        # Check if any user field is in groupby
        fields_in_groupby = [field for field in user_fields_to_filter if field in groupby]

        if fields_in_groupby:
            filtered_result = []

            for group in result:
                should_include = True

                for field in fields_in_groupby:
                    if group.get(field):
                        if field == 'team_leader_ids':
                            # Many2many field - get first ID from tuple (id, name)
                            user_id = group[field][0]
                        else:
                            # Many2one field (user_id) - get first ID from tuple (id, name)
                            user_id = group[field][0]

                        user = self.env['res.users'].browse(user_id)
                        if not user.active:
                            should_include = False
                            break

                if should_include:
                    filtered_result.append(group)

            return filtered_result

        return result
