# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta

import odoorpc
import pytz
from lxml import etree
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

from ..utils import get_connection

_logger = logging.getLogger(__name__)

AKTIV_CLOSED_STATES = ('done', 'cancel')


class ProjectTask(models.Model):
    _inherit = "project.task"

    def _get_default_developer(self):
        """Set default developer if single developer for project."""
        project_id = self._context.get("project_id") or self.env.context.get(
            "default_project_id"
        )
        project_developer = self.env["project.project"].browse(project_id).developer_ids
        if len(project_developer) == 1:
            return project_developer.ids


    def web_read(self, specification):
        if 'project_id' not in specification:
            return super().web_read(specification)
        spec_without_project = {k: v for k, v in specification.items() if k != 'project_id'}
        result = super().web_read(spec_without_project)
        for record_data, record in zip(result, self):
            project = record.sudo().project_id
            record_data['project_id'] = (
                {'id': project.id, 'display_name': project.sudo().display_name}
                if project else False
            )
        return result

    def get_tasks(self):
        """Method to get tasks from pm tool using genreic method."""
        odoo_conn = False
        try:
            odoo_conn = get_connection()
        except Exception as e:
            return []
        if odoo_conn:
            task_ids = odoo_conn.env["project.task"].search_read(
                [("B2C_task_sync", "=", True)], fields=["name"]
            )
            tasks = []
            for task in task_ids:
                tsk = (str(task.get("id")), task.get("name"))
                tasks.append(tsk)
            return tasks
        return []

    go_live_date = fields.Date(compute='_compute_go_live_date', store=True, readonly=False)
    deployment_type = fields.Selection(related='project_id.deployment_type',
        help="Use to make Go Live Date field readonly if Deployment Type (In Project) is Phase Wise", store=True)
    qa_ids = fields.One2many("quality.analysis", "task_id", string="Quality Analysis")
    state = fields.Selection(
        selection=[
            ("new", "Planned"),
            ("approval", "Customer Approval"),
            ("dev", "Development"),
            ("call_consult", "Calls/Consulting"),
            ("cd_review", "Code Review"),
            ("qa", "QA Testing"),
            ("redevelop", "Re-Development"),
            ("cust_review", "Customer Review"),
            ("done", "Done"),
            ("cancel", "Cancel"),
            ("on_hold", "On Hold"),
            ("ready_deploy", "Ready for Deployment"),
            ("apps", "Apps")
        ],
        default="new",
        group_expand="_group_expand_states",
    )
    def _compute_state(self):
        pass

    def _inverse_state(self):
        pass

    @property
    def OPEN_STATES(self):
        return [v for v in self._fields['state'].get_values(self.env) if v not in AKTIV_CLOSED_STATES]

    @api.depends('state')
    def _compute_is_closed(self):
        for task in self:
            task.is_closed = task.state in AKTIV_CLOSED_STATES

    def _search_is_closed(self, operator, value):
        if operator == 'in':
            searched_states = list(AKTIV_CLOSED_STATES)
        elif operator == 'not in':
            searched_states = self.OPEN_STATES
        else:
            return NotImplemented
        return [('state', 'in', searched_states)]

    success_ratio = fields.Float(
        "Success", compute="_compute_test_case_count", store=True
    )
    total_tasks_performed = fields.Integer(
        "Total Tasks Performed", compute="_compute_test_case_count", store=True
    )
    passed_tests = fields.Integer(
        "Passed", compute="_compute_test_case_count", store=True
    )
    failed_tests = fields.Integer(
        "Failed", compute="_compute_test_case_count", store=True
    )
    post_performed_test_case = fields.Integer(
        "Post Performed Task", compute="_compute_test_case_count", compute_sudo=True,
    )
    post_passed_test_case = fields.Integer(
        "Post Passed Task", compute="_compute_test_case_count", compute_sudo=True,
    )
    post_failed_test_case = fields.Integer(
        "Post Failed Task", compute="_compute_test_case_count", compute_sudo=True,
    )
    post_test_ratio = fields.Float(
        "Post Success Test Case", compute="_compute_test_case_count", compute_sudo=True,
    )
    is_delete = fields.Boolean(string="Is qa line deleted?", default=False)
    qa_line_length = fields.Integer(string="Length of QA Lines", default=0)
    user_ids = fields.Many2many(string="Developers", default=_get_default_developer)
    is_user = fields.Boolean(default=False, compute="_compute_readonly_user")
    is_team_leader = fields.Boolean(default=False, compute="_compute_readonly_team_leader")
    qa_remark_note = fields.Html(string="QA Notes", translate=True)
    note = fields.Html(string="Notes", translate=True)
    is_bug = fields.Boolean(
        string="Is there any bugs?", compute="_compute_bugs", store=True
    )
    is_production_bug = fields.Boolean(string="Is production bug ?")
    bugs_type = fields.Selection(
        [
            ("production_bug", "Production Bug"),
            ("staging_bug", "Staging Bug"),
        ],
        string="Bug Type",
    )
    hide_approved_hours = fields.Boolean(
        compute="_compute_hide_approved_hours",
        string="Effective Hours Access",
    )

    task_completion = fields.Boolean(
        string="Task Can be accomplished",
        compute="_compute_task_accomplish",
        default=False,
    )
    task_type_id = fields.Many2one(
        'task.type',
        string="Task Type",
    )
    task_type_name = fields.Char(
        compute='_compute_task_type_name',
        string='Task Type Name',
        store=True
    )
    is_code_reviewer = fields.Boolean(
        string="Is code reviewer", compute="_compute_code_reviewer", default=False
    )
    urgent_task = fields.Boolean(string="Urgent task")

    # QA related fields for timesheet data
    qa_deadline = fields.Date(string="QA Deadline")
    qa_billed_hours = fields.Float(string="QA Productive Hours", related="qa_approved_hr")
    qa_start_date = fields.Date(string="QA Start Date")
    qa_hours = fields.Float(string="QA Planned Hours", default=0.0)

    # Compute fields
    qa_spent_hr = fields.Float(string="QA Spent Hours", compute="_compute_qa_hours", compute_sudo=True)
    qa_approved_hr = fields.Float(
        string="QA Approved Hours", compute="_compute_qa_hours", store=True
    )
    qa_remain_hr = fields.Float(string="QA Remaining Approval Hours", compute="_compute_qa_hours", compute_sudo=True)

    # Developer related fields for timesheets.
    dev_deadline = fields.Date(string="Dev Deadline")
    dev_billed_hours = fields.Float(string="Dev Productive Hours", related="dev_approved_hr")
    dev_start_date = fields.Date(string="Dev Start Date")
    dev_hours = fields.Float(string="Dev Planned Hours")

    #  Compute fields to calculate development hours
    dev_spent_hr = fields.Float(
        string="Dev Spent Hours",
        compute="_compute_qa_hours",
        compute_sudo=True,
    )
    dev_approved_hr = fields.Float(
        string="Dev Approved Hours", compute="_compute_qa_hours", store=True
    )
    dev_remain_hr = fields.Float(
        string="Remaining Approval Hours",
        compute="_compute_qa_hours",
        compute_sudo=True,
    )

    tech_description = fields.Html()
    task_state_count = fields.Integer(string="Re-development", store=True, default=0, copy=False)
    qa_state_count = fields.Integer(string="QA state count", store=True, default=0, copy=False)
    code_reviewer_ids = fields.Many2many(
        "res.users",
        "task_cr_rel",
        "task_id",
        "user_id",
        string="Code Reviewer",
        tracking=True,
    )
    task_qa_ids = fields.Many2many(
        "res.users", "task_qa_rel", "task_id", "user_id", string="QA", tracking=True
    )
    is_qa = fields.Boolean(string="Is QA", compute="_compute_qa", default=False, compute_sudo=True)
    is_developer = fields.Boolean(
        string="Is Developer", compute="_compute_developer", default=False, compute_sudo=True
    )
    approved_hours = fields.Float(
        string="Approved Hours", compute="_compute_approved_hours"
    )
    user_manual = fields.Text(
        string="User Manual"
    )
    pm_tool_task_id = fields.Char(related="project_id.pm_tool_task_id", store=True)
    pm_tool_task_name = fields.Char(related="project_id.pm_tool_task_name", store=True)
    pm_tool_tasks = fields.Selection(
        selection=get_tasks, copy=False
    )
    est_st_dt = fields.Date("Estimated Start Date", related="dev_start_date")

    """ Override field to calculate planned hours based on QA and Developer Hours """
    planned_hours = fields.Float(
        compute="_compute_planned_hours",
        store=True,
        readonly=False
    )
    """
        Add one Boolean field which show only project manager field is True.
    """
    subtask_planned_hours = fields.Float("Sub-tasks Planned Hours", compute='_compute_subtask_planned_hours',
        help="Sum of the time planned of all the sub-tasks linked to this task. Usually less than or equal to the initially planned time of this task.")
    # subtask_planned_hour = fields.Float(string="Initially Planned Hour for Subtasks", compute="compute_planned_hour")
    billed_hours = fields.Float(string="Billed Hours", compute="_compute_billed_hours")
    unbilled_hours = fields.Float(string="Unbilled Hours", compute="_compute_unbilled_hours")
    unbilled_hours_on_sub_task = fields.Float('Unbilled on Sub-Task', compute="_compute_unbilled_hours_on_subtask")
    productive_hours_on_sub_task = fields.Float("Productive Hours on Sub-Task", compute='_compute_productive_hours_on_subtask')

    """ Added fields for branch name """
    development_branch_name = fields.Char(
        string="Developer Branch"
    )
    qa_branch_name = fields.Char(
        string="QA Branch"
    )

    is_visible_dashboard = fields.Boolean(string="Is Visible Dashboard?")
    dont_remember_parent_task = fields.Boolean(string="Don't remember the parent task")
    # override parent_id fields and added the tracking
    parent_id = fields.Many2one(
        'project.task',
        string='Parent Task',
        index=True,
        tracking=True
    )
    skip_quality_check = fields.Boolean('Skip Quality Check')
    hide_re_development_btn = fields.Boolean(compute='_compute_hide_re_development_btn')

    @api.model
    def get_view(self, view_id=None, view_type='list', **kwargs):
        res = super().get_view(view_id, view_type, **kwargs)
        if view_type == 'form':
            user = self.env['res.users'].browse(self.env.context.get('uid', False))
            restricted_groups = user._get_restricted_group()
            if user.has_group("project.group_project_user") and not any(user.has_group(group) for group in restricted_groups):
                doc = etree.XML(res['arch'])
                for node in doc.xpath("//field[@name='timesheet_ids']/tree/field[@name='effective_hours']"):
                    node.set("readonly", "1")
                res['arch'] = etree.tostring(doc, encoding='unicode')
            else:
                doc = etree.XML(res['arch'])
                for node in doc.xpath("//field[@name='timesheet_ids']/tree/field[@name='effective_hours']"):
                    node.set("readonly", "0")
                res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def _compute_hide_re_development_btn(self):
        for rec in self:
            if rec.task_type_name in ('Consulting','Training','Apps'):
                rec.hide_re_development_btn = True
            elif rec.is_code_reviewer and rec.state == 'cd_review':
                rec.hide_re_development_btn = False
            elif rec.is_qa and rec.state == 'qa':
                rec.hide_re_development_btn = False
            elif rec.state in ('new', 'done','dev','redevelop', 'qa', 'cd_review' 'cust_review', 'approval', 'ready_deploy', 'cancel', 'on_hold'):
                rec.hide_re_development_btn = True
            else:
                rec.hide_re_development_btn = True

    @api.depends('project_id.go_live_date')
    def _compute_go_live_date(self):
        """
        If Deployment Type (In Project) is Phase Wise or False,
        Copy Go Live Date from Project to Task
        """
        for task in self.filtered(lambda t: t.deployment_type in [False, 'phase_wise']):
            task.go_live_date = task.project_id.go_live_date

    @api.onchange("project_id")
    def _onchange_project_id(self):
        """Method to call when there is change in the start Date"""
        user = self.env.user
        user_groups = set(user.group_ids.get_external_id().values())
        restricted_groups = set(user._get_restricted_manager_group())
        if self.project_id and not self.project_id.is_sop_bank:
            if user != self.env.ref("base.user_admin"):
                if not restricted_groups.intersection(user_groups) and self.env.user.id not in self.project_id.team_leader_ids.ids and self.env.user.id not in self.project_id.consultant_ids.ids:
                    raise ValidationError(
                        _("You can not create task for this project!")
                    )
    
    def _compute_hide_approved_hours(self):
        for task in self:
            task.hide_approved_hours = False
            user = self.env.user
            if self.env.ref("base.user_admin").id != user.id:
                if (
                        user.has_group("project.group_project_user")
                        and not user.has_group("aktiv_pms.group_aktiv_project_team_leader")
                        and not user.has_group("project.group_project_manager")
                        and not user.has_group("aktiv_pms.group_aktiv_project_manager")
                        and not user.has_group("aktiv_pms.group_aktiv_project_functional")
                        and not user.has_group("aktiv_pms.group_aktiv_project_QA")
                ):
                    task.hide_approved_hours = True

    def add_task_type(self):
        for rec in self.search([]):
            if rec.task_type == "customization":
                rec.task_type_id = self.env.ref("aktiv_pms.task_type_customization").id
            if rec.task_type == "consulting":
                rec.task_type_id = self.env.ref("aktiv_pms.task_type_consulting").id
            if rec.task_type == "qa":
                rec.task_type_id = self.env.ref("aktiv_pms.task_type_qa").id
            if rec.task_type == "communication":
                rec.task_type_id = self.env.ref("aktiv_pms.task_type_communication").id
            if rec.task_type == "apps":
                rec.task_type_id = self.env.ref("aktiv_pms.task_type_apps").id
            if rec.task_type == "training":
                rec.task_type_id = self.env.ref("aktiv_pms.task_type_training").id

    def add_is_production_bug(self):
        for rec in self.search([]):
            if rec.is_production_bug:
                rec.bugs_type = 'production_bug'
                rec.dont_remember_parent_task = True

    @api.depends('task_type_id')
    def _compute_task_type_name(self):
        for task in self:
            task.task_type_name = ''
            if task.task_type_id:
                task.task_type_name = task.task_type_id.name

    @api.depends('child_ids.planned_hours')
    def _compute_subtask_planned_hours(self):
        """Method will be used for compute the subtasks planed hours"""
        for task in self:
            task.subtask_planned_hours = sum(child_task.planned_hours + child_task.subtask_planned_hours for child_task in task.child_ids)


    def on_hold(self):
        """method to open wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reason for On Hold',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.task.wizard',
            'target': 'new',
        }

    def ready_deployment(self):
        """method to change state to ready deploy and send mail to user"""
        self.write({'state': 'ready_deploy'})
        template = self.env.ref("aktiv_pms.mail_template_for_project_task_deployment")
        for developer in self.user_ids:
            if self.user_ids:
                email_values = {
                    "email_to": developer.partner_id.email,
                }
                template.with_context(state="Ready for Deployment").send_mail(
                    self.id, force_send=True, email_values=email_values, email_layout_xmlid=False
                )

    @api.depends("qa_hours", "dev_hours")
    def _compute_planned_hours(self):
        for task in self:
            if task.qa_hours or task.dev_hours:
                task.planned_hours = task.qa_hours + task.dev_hours

    @api.depends("qa_billed_hours", "dev_billed_hours")
    def _compute_billed_hours(self):
        for task in self:
            if task.qa_billed_hours or task.dev_billed_hours:
                task.billed_hours = task.qa_billed_hours + task.dev_billed_hours
            else:
                task.billed_hours = 0.0

    @api.depends("planned_hours", "approved_hours")
    def _compute_unbilled_hours(self):
        """Method will be used for compute the unbilled Hour based on productive hour"""
        for task in self:
            if task.planned_hours:
                task.unbilled_hours = task.planned_hours - task.approved_hours
            else:
                task.unbilled_hours = 0.0

    @api.depends('child_ids.planned_hours')
    def _compute_unbilled_hours_on_subtask(self):
        """Method will be used for compute the unbilled Hour of subtask based on productive hour"""
        for task in self:
            task.unbilled_hours_on_sub_task = sum(child_task.unbilled_hours for child_task in task.child_ids)

    @api.depends('child_ids.approved_hours')
    def _compute_productive_hours_on_subtask(self):
        """Method will be used for compute the Productive Hour of subtask."""
        for task in self:
            task.productive_hours_on_sub_task = sum(child_task.approved_hours for child_task in task.child_ids)

    @api.depends('timesheet_ids.unit_amount', 'timesheet_ids.approved_hours')
    @api.depends('timesheet_ids.unit_amount', 'timesheet_ids.approved_hours')
    def _compute_qa_hours(self):
        self.qa_approved_hr, self.qa_spent_hr, self.qa_remain_hr = 0.0, 0.0, 0.0
        self.dev_approved_hr, self.dev_spent_hr, self.dev_remain_hr = 0.0, 0.0, 0.0
        for task in self:
            task.dev_spent_hr = sum(
                task.timesheet_ids.filtered(lambda t: t.user_type == "dev").mapped(
                    "unit_amount"
                )
            )
            task.dev_approved_hr = sum(
                task.timesheet_ids.filtered(
                    lambda t: t.user_type == "dev" and t.state == "approved"
                ).mapped("approved_hours")
            )
            task.qa_spent_hr = sum(
                task.timesheet_ids.filtered(lambda t: t.user_type == "qa").mapped(
                    "unit_amount"
                )
            )
            task.qa_approved_hr = sum(
                task.timesheet_ids.filtered(
                    lambda t: t.user_type == "qa" and t.state == "approved"
                ).mapped("approved_hours")
            )
            task.qa_remain_hr = task.qa_hours - task.qa_spent_hr
            task.dev_remain_hr = task.dev_hours - task.dev_spent_hr

    @api.onchange("urgent_task")
    def onchange_urgent_task(self):
        for rec in self:
            self.priority = "0"
            if self.urgent_task:
                self.priority = "1"

    @api.depends("timesheet_ids.approved_hours")
    def _compute_approved_hours(self):
        for task in self:
            task.approved_hours = round(
                sum(
                    task.timesheet_ids.filtered(
                        lambda approved: approved.state == "approved"
                    ).mapped("approved_hours")
                ),
                2,
            )

    @api.onchange("qa_hours")
    def _onchange_qa_deadline(self):
        """Method to compute the qa deadline."""

        if self.qa_hours:
            current_dt = datetime.now()
            qa_hours_dt = timedelta(hours=self.qa_hours)
            user_tz = pytz.timezone(self.env.context.get("tz") or self.enc.user.tz)
            local_date = user_tz.localize(current_dt).utcoffset()
            hrs, min, sec = str(local_date).split(":")
            total_dt = current_dt + qa_hours_dt
            local_dt = total_dt + timedelta(hours=int(hrs), minutes=int(min))
            if (local_dt.strftime("%A")) in ["Saturday", "Sunday"]:
                self.qa_deadline = total_dt + timedelta(days=2)
            else:
                self.qa_deadline = total_dt
        else:
            self.qa_deadline = False

    def _compute_code_reviewer(self):
        """Method to check code reviewer is logged in"""

        for rec in self:
            rec.is_code_reviewer = False
            current_user = self.env["res.users"].browse(self.env.uid)
            if (
                    current_user.id in self.code_reviewer_ids.ids
                    or current_user.has_group("aktiv_pms.group_aktiv_project_manager")
                    or current_user.has_group("project.group_project_manager")
                    or current_user.id in self.project_id.team_leader_ids.ids
            ):
                rec.is_code_reviewer = True

    def _compute_qa(self):
        """Method to check QA is logged in"""

        for rec in self:
            rec.is_qa = False
            current_user = self.env["res.users"].browse(self.env.uid)
            if (
                    current_user.id in self.task_qa_ids.ids
                    or current_user.has_group("aktiv_pms.group_aktiv_project_manager")
                    or current_user.has_group("project.group_project_manager")
                    or current_user.id in self.project_id.team_leader_ids.ids
            ):
                rec.is_qa = True

    def _compute_developer(self):
        """Method to check Developer is logged in"""

        for rec in self:
            rec.is_developer = False
            current_user = self.env["res.users"].browse(self.env.uid)
            if (
                    current_user.id in self.user_ids.ids
                    or current_user.has_group("aktiv_pms.group_aktiv_project_manager")
                    or current_user.has_group("project.group_project_manager")
                    or current_user.id in self.project_id.team_leader_ids.ids
            ):
                rec.is_developer = True

    @api.constrains('project_id', 'pm_tool_task_id')
    def _check_pm_tool_task_id(self):
        user = self.env.user
        user_groups = set(user.group_ids.get_external_id().values())
        restricted_groups = set(user._get_restricted_manager_group())
        if user != self.env.ref("base.user_admin"):
            if not restricted_groups.intersection(user_groups) and self.env.user.id not in self.project_id.team_leader_ids.ids and self.env.user.id not in self.project_id.consultant_ids.ids:
                for task in self:
                    if task.project_id and not task.project_id.is_sop_bank:
                        if task and not task.pm_tool_task_id:
                            raise UserError(
                                "Unable to create a task without an associated project! "
                                "To proceed, please create a project in the B2B Portal using "
                                "'Create B2B Project' button from the Project View."
                            )
                        raise ValidationError(
                            _("You can not create task for this project!")
                        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['state'] = 'new'
        task_recs = super(ProjectTask, self).create(vals_list)
        
        for task in task_recs:
            vals_dict = {}
            if task.project_id:
                vals_dict['tag_ids'] = [(6, 0, task.project_id.tag_ids.ids)]
            if task.task_type_id.name == "Apps":
                vals_dict['state'] = "apps"
            if vals_dict:
                task.write(vals_dict)
            
        return task_recs

    def write(self, vals):
        if 'project_id' in vals:
            project_id = self.env["project.project"].browse(vals['project_id'])
            vals['tag_ids'] = [(6, 0, project_id.tag_ids.ids)]
            vals['state'] = 'new'

        if 'task_type_id' in vals:
            task_type = self.env['task.type'].browse(vals['task_type_id'])
            if task_type.name == 'Apps':
                vals['state'] = 'apps'

        return super(ProjectTask, self).write(vals)

    def copy(self, default=None):
        default = dict(default or {})
        res = super(ProjectTask, self).copy(default)
        user = self.env.user
        user_groups = set(user.group_ids.get_external_id().values())
        restricted_groups = set(user._get_restricted_manager_group())
        if self.project_id and not self.project_id.is_sop_bank:
            if user != self.env.ref("base.user_admin"):
                if not restricted_groups.intersection(user_groups) and self.env.user.id not in self.project_id.team_leader_ids.ids and self.env.user.id not in self.project_id.consultant_ids.ids:
                    raise ValidationError(
                        _("You can not create task for this project!")
                    )
        return res

    @api.depends("date_deadline")
    def _compute_task_accomplish(self):
        """Method to compute the number of days in to accomplish task."""

        for rec in self:
            rec.task_completion = False
            if rec.date_deadline and rec.planned_hours:
                deadline = rec.date_deadline
                today = fields.Date.today()
                if isinstance(deadline, datetime):
                    deadline = deadline.date()
                days = deadline - today
                business_days = {
                    (today + timedelta(days=x))
                    for x in range(days.days + 1)
                    if (today + timedelta(days=x)).isoweekday() <= 5
                }
                task_completion_hours = (len(business_days) * 8) - rec.effective_hours
                if rec.remaining_hours >= task_completion_hours:
                    rec.task_completion = True
                if rec.remaining_hours == 0.0:
                    rec.task_completion = False

    @api.depends("qa_ids")
    def _compute_bugs(self):
        """Method to check if bug."""

        self.is_bug = False
        if self.qa_ids:
            self.is_bug = [
                True
                for rec in self.qa_ids
                if (rec.outcomes == "bug" and rec.is_updated is False)
            ]

    @api.depends("qa_ids")
    def _compute_test_case_count(self):
        """Method to count the test cases."""

        for task in self:
            task.passed_tests, task.failed_tests = 0, 0
            task.post_performed_test_case, task.post_passed_test_case = 0, 0
            task.post_failed_test_case, task.post_test_ratio = 0, 0
            task.success_ratio, task.total_tasks_performed = 0, 0
            if task.qa_ids:
                success = len(
                    task.qa_ids.filtered(
                        lambda l: l.outcomes == "expected" and l.is_new != True
                    )
                )
                post_success = len(
                    task.qa_ids.filtered(
                        lambda l: l.outcomes == "expected" and l.is_new == True
                    )
                )
                task.total_tasks_performed = len(
                    task.qa_ids.filtered(lambda p: p.is_new != True)
                )
                task.passed_tests = len(
                    task.qa_ids.filtered(
                        lambda p: p.outcomes == "expected" and p.is_new != True
                    )
                )
                task.failed_tests = len(
                    task.qa_ids.filtered(
                        lambda f: f.outcomes == "bug" and f.is_new != True
                    )
                )
                task.post_performed_test_case = len(
                    task.qa_ids.filtered(lambda p: p.is_new == True)
                )
                task.post_passed_test_case = len(
                    task.qa_ids.filtered(
                        lambda p: p.outcomes == "expected" and p.is_new == True
                    )
                )
                task.post_failed_test_case = len(
                    task.qa_ids.filtered(
                        lambda p: p.outcomes == "bug" and p.is_new == True
                    )
                )
                if task.post_performed_test_case > 0:
                    task.post_test_ratio = (
                                                   post_success * 100
                                           ) / task.post_performed_test_case
                if task.total_tasks_performed > 0:
                    task.success_ratio = (success * 100) / task.total_tasks_performed

    #@api.depends("is_user")
    def _compute_readonly_user(self):
        """Method to make fields readonly for related groups"""

        for rec in self:
            rec.is_user = False
            current_user = self.env["res.users"].browse(self.env.uid)
            if (
                    current_user.has_group("project.group_project_user")
                    and not current_user.has_group("project.group_project_manager")
                    and not current_user.has_group("aktiv_pms.group_aktiv_project_manager")
                    # and not current_user.has_group("aktiv_pms.group_aktiv_project_team_leader")
                    and self.env.uid != SUPERUSER_ID and self.env.uid not in rec.project_id.consultant_ids.ids
            ):
                rec.is_user = True

    @api.depends("is_team_leader")
    def _compute_readonly_team_leader(self):
        """Method to make fields readonly for related groups"""

        for rec in self:
            rec.is_team_leader = False
            current_user = self.env["res.users"].browse(self.env.uid)
            if (
                    current_user.has_group("project.group_project_user")
                    and not current_user.has_group("project.group_project_manager")
                    and not current_user.has_group("aktiv_pms.group_aktiv_project_manager")
                    and current_user.has_group("aktiv_pms.group_aktiv_project_team_leader")
                    and current_user.id in rec.project_id.team_leader_ids.ids
            ):
                rec.is_team_leader = True

    def get_task_url(self):
        """This method will return url of task in mail template"""
        return self._notify_get_action_link('view')

    def action_start_task(self):
        """Button action  to start task."""
        if self.task_type_name == 'QA':
            vals = {"state": 'qa'}
        else:
            vals = {"state": 'dev'}
        self.write(vals)
                
        template = self.env.ref("aktiv_pms.mail_template_for_project_task")
        for developer in self.user_ids:
            email_values = {
                "email_to": developer.partner_id.email,
            }
            template.with_context(state="Development").send_mail(
                self.id, force_send=True, email_values=email_values, email_layout_xmlid=False
            )

    def action_testing_qa_bugs(self):
        self.write({"state": "qa"})

    def action_code_review(self):
        """Button action to open wizard and check the Quality Checks"""
        if self.skip_quality_check:
            self.state = "cd_review"
        else:
            quality_check = self.env["quality.check.points"].search([])
            view = self.env.ref("aktiv_pms.view_quality_check_points_wizard")
            data = self.env["quality.check.points.wizard"].create({
                "quality_check_ids": [
                    (
                        0,
                        0,
                        {
                            "name": qc.name,
                            "is_required": qc.is_required,
                        },
                    )
                    for qc in quality_check
                ]
            })
            if self.task_state_count < 1:
                if data.quality_check_ids:
                    return {
                        "name": _("Code Quality Check"),
                        "type": "ir.actions.act_window",
                        "view_mode": "form",    
                        "res_model": "quality.check.points.wizard",
                        "views": [(view.id, "form")],
                        "view_id": view.id,
                        "target": "new",
                        "context": {
                            "default_quality_check_ids": data.quality_check_ids.ids
                        },
                    }
                else:
                    raise ValidationError(_("There are no Quality Checks for Checking."))
            else:
                self.state = "cd_review"

    def waiting_for_ca(self):
        self.write({"state": "approval"})

    def action_calls_consulting(self):
        self.write({"state": "call_consult"})

    def aktiv_pms_cancel(self):
        if self.child_ids:
            sub_tasks = self.child_ids.filtered(lambda x:x.state != 'cancel')
            if sub_tasks:
                self |= sub_tasks
        self.write({"state": "cancel"})

    def action_cus_review(self):
        """Button action to send task for customer review."""
        self.write({"state": "cust_review"})
        template = self.env.ref("aktiv_pms.mail_template_for_project_task")
        email_values = {
            "email_to": self.project_id.user_id.email,
        }
        template.with_context(state="Review").send_mail(
            self.id, force_send=True, email_values=email_values, email_layout_xmlid=False
        )

    def action_qa_test(self):
        self.qa_state_count += 1
        self.write(
            {
                "task_qa_ids": [
                    (4, task_qa_id)
                    for task_qa_id in self.project_id.task_qa_ids.ids[:1]
                ],
                "state": "qa",
            }
        )
        template = self.env.ref("aktiv_pms.mail_template_for_project_task")
        for developer in self.task_qa_ids:
            email_values = {
                "email_to": developer.partner_id.email,
            }
            template.with_context(state="QA").send_mail(
                self.id, force_send=True, email_values=email_values, email_layout_xmlid=False
            )

    def action_re_development(self):
        """Button action to send task for redevelopment"""

        self.qa_ids.write({"is_updated": True})
        self.task_state_count += 1
        self.write({"state": "redevelop"})
        template = self.env.ref("aktiv_pms.mail_template_for_project_task")
        for developer in self.user_ids:
            email_values = {
                "email_to": developer.partner_id.email,
            }
            template.with_context(state="Re-Development").send_mail(
                self.id, force_send=True, email_values=email_values, email_layout_xmlid=False
            )

    def action_done(self):
        """Button action to mark task done."""
        if self.child_ids:
            sub_tasks = self.child_ids.filtered(lambda x:x.state != 'done')
            if sub_tasks:
                self |= sub_tasks
        self.write({"state": "done"})

    def _group_expand_states(self, states, domain):
        return [key for key, val in type(self).state.selection]

    def _log_logging(self, message, function_name):
        log_data = {
            "name": "Sync Timesheet",
            "type": "server",
            "level": "info",
            "dbname": self.env.cr.dbname,
            "message": message,
            "func": function_name,
            "path": self._name,
            "line": "0",
        }
        self.env["ir.logging"].sudo().create(log_data)
        self.env.cr.commit()

    def display_notification(self, title, message, sticky):
        """
        Helper method to display notifications.
        """
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "sticky": sticky,
            },
        }

    def sync_timesheet_to_pm_tool(self):

        """
        Method which will connect the db of pm tool and create the timesheet data
        in aktiv pmtool.

        Added try except block to avoid error when connection cant be established
        due to insufficiant or wrong data.

        This method will return success message if there timesheets are synced of
        current user and if there is no timesheet to sync then it will raise
        warning that there is no timesheet entriesto sync.
        """

        try:
            odoo_conn = get_connection(self.env)
        except Exception as e:
            raise ValidationError(e)

        if not odoo_conn:
            return self.display_notification(_("Error!"), _("Failed to connect to PM Tool."), True)

        user_name = self.env.user.user_name
        user_id = odoo_conn.env["res.users"].search([("login", "=", user_name)], limit=1)
        if not user_id:
            raise ValidationError(_("User not found in PM Tool."))


        employee_id = odoo_conn.env["hr.employee"].search([("user_id", "in", user_id)], limit=1)
        if not employee_id:
            raise ValidationError(_("Employee not found in PM Tool."))

        project_task_id = int(self.pm_tool_task_id)
        project_task = odoo_conn.env["project.task"].read(project_task_id, ['project_id'])
        if not project_task:
            raise ValidationError(_("Task not found in PM Tool."))

        success_message = _("Timesheets synced successfully!")
        no_timesheet_message = _("No timesheet entries found to sync.")

        timesheets_to_sync = self.timesheet_ids.filtered(lambda t: t.data_sync == "not_sync" and t.employee_id.user_id.user_name == user_name
                                                         and (t.unit_amount != 0 or (t.unit_amount == 0 and t.pmtool_timesheet_id)))
        if not timesheets_to_sync:
            return self.display_notification(_("Warning!"), no_timesheet_message, False)

        try:
            for timesheet in timesheets_to_sync:
                # Enforces date lock check for non-project managers before sync.
                if not self.env.user.has_group('project.group_project_manager'):
                    timesheet._check_lock_date(timesheet.date)
                timehseet_vals = {"data_sync": "sync"}
                date = fields.Date.to_string(timesheet.date)
                vals = {
                    "task_id": project_task_id,
                    "date": date,
                    "name": timesheet.name,
                    "unit_amount": timesheet.unit_amount,
                    "effective_hours": timesheet.effective_hours,
                    "productive_hours": timesheet.approved_hours,
                    "project_id": project_task[0].get('project_id')[0],
                    "employee_id": employee_id[0],
                }

                pm_ts = odoo_conn.env["account.analytic.line"].browse(int(timesheet.pmtool_timesheet_id))
                if pm_ts:
                    pm_ts.write(vals)
                else:
                    timesheet_id = odoo_conn.env["account.analytic.line"].create(vals)
                    timehseet_vals.update({"id": timesheet.id, "pmtool_timesheet_id": timesheet_id})
                    

                timesheet.write(timehseet_vals)
                self.env.cr.commit()

            return self.display_notification(_("Success"), success_message, False)

        except Exception as e:
            raise ValidationError(e)

    @api.model
    def auto_sync_timesheet_to_pm_tool(self):
        """
        Method which will connect the db of pm tool and create the timesheet data
        in aktiv pmtool.
        Added try except block to avoid error when connection cant be established
        due to insufficient or wrong data.
        This method will return a success message if there are timesheets synced for
        the current user. If there are no timesheets to sync, it will raise a
        warning that there are no timesheet entries to sync.
        """
        try:
            odoo_conn = get_connection(self.env)
        except Exception as e:
            self._log_logging(e, "sync_timesheet_to_pm_tool")
            return False

        if not odoo_conn:
            return False

        timesheets_to_sync = self.env['account.analytic.line'].search([
            ('data_sync', '=', 'not_sync'),
            ('task_id.pm_tool_task_id', '!=', False),
            ('date', '>=', '2024-03-01'),
            ])

        b2b_tool_tasks = [int(timesheet_task.pm_tool_task_id) for timesheet_task in timesheets_to_sync.mapped('task_id')]

        task_project_ids = odoo_conn.env["project.task"].search_read(
                [("id", "in", b2b_tool_tasks)], fields=["id", "project_id"]
            )
        b2b_project_task_map = {project['id']: project['project_id'][0] for project in task_project_ids}

        for timesheet in timesheets_to_sync:
            timesheet_vals = {"data_sync": "sync"}
            b2b_task_id = int(timesheet.task_id.pm_tool_task_id)
            project_id = b2b_project_task_map.get(b2b_task_id)
            if not project_id:
                self._log_logging(
                    "Project for task [%s] not found on PM Tool! " % (b2b_task_id),
                    "sync_timesheet_to_pm_tool",
                )
                continue
            date = timesheet.date.strftime("%Y-%m-%d")
            timesheet_user = timesheet.user_id.user_name
            b2b_user_id = odoo_conn.env["res.users"].search([("login", "=", timesheet_user)], limit=1)
            if not b2b_user_id:
                continue
            b2b_employee_id = odoo_conn.env["hr.employee"].search([("user_id", "in", b2b_user_id)], limit=1)
            if not b2b_employee_id:
                self._log_logging(
                    "Employee for userID:%s not found on PM Tool!" % (b2b_user_id),
                    "sync_timesheet_to_pm_tool",
                )
                continue
            update_vals = {}
            try:
                vals = {
                    "task_id": b2b_task_id,
                    "date": date,
                    "name": timesheet.name,
                    "unit_amount": timesheet.unit_amount,
                    "effective_hours": timesheet.effective_hours,
                    "productive_hours": timesheet.approved_hours,
                    "project_id": project_id,
                    # "b2c_timesheet_sync": True,
                    "employee_id": b2b_employee_id[0] if b2b_employee_id else False,
                }
                pm_ts = odoo_conn.env["account.analytic.line"].browse(
                    int(timesheet.pmtool_timesheet_id)
                )
                if pm_ts:
                    pm_ts.write(vals)
                else:
                    timesheet_id = odoo_conn.env["account.analytic.line"].create(vals)
                    timesheet_vals.update({"pmtool_timesheet_id": timesheet_id, "data_sync": "sync"})
                
            except Exception as e:
                self._log_logging(
                    e,
                    "sync_timesheet_to_pm_tool",
                )
                continue
            timesheet.write(timesheet_vals)
            self.env.cr.commit()
        return True


    def fetch_project_task_ids(self):
        odoo_conn = get_connection(self.env)
        tasks = self.env["project.task"].search([])
        for rec in tasks:
            task_ids = odoo_conn.env["project.task"].search_read(
                        [("id", "=", rec.pm_tool_tasks)], fields=["id", "name", "project_id"]
                    )
            if task_ids:
                rec.project_id.update({'pm_tool_task_id': task_ids[0].get('id'),
                                      'pm_tool_task_name': task_ids[0].get('name'),
                                      'pm_tool_project_id': task_ids[0].get('project_id')[0],
                                    })

    def action_open_quality_analysis(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Quality Analysis",
            "res_model": "quality.analysis",
            "view_mode": "list,form",
            "domain": [("task_id", "=", self.id)],
            "context": {"default_task_id": self.id},
            "target": "current",
        }
