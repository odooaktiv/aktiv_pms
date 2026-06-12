# -*- coding: utf-8 -*-

import json

from lxml import etree
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Date
from ..utils import get_connection
from datetime import timedelta


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    state = fields.Selection(
        [("approval", "Pending For Approval"), ("approved", "Approved")],
        default="approval",
    )
    approved_hours = fields.Float(string="Productive Hours")
    last_approval_reason = fields.Text(string="Last Approval Reason", copy=False)
    approved_hours_logs = fields.Text(string="Productive Hours Logs",
        copy=False, readonly=True)
    qa_timesheet = fields.Boolean(
        string="QA Timesheet", compute="_compute_qa_timesheet", store=True
    )
    data_sync = fields.Selection(
        [("not_sync", "Not Sync"), ("sync", "Sync")],
        "Timesheet Sync",
        default="not_sync",
    )
    pmtool_timesheet_id = fields.Char("PM Tool Task Id")
    user_type = fields.Selection([("dev", "Developer"), ("qa", "QA")])
    remaining_hours = fields.Float(string="Remaining Approval Hours", default=0)
    checked = fields.Boolean(string="Productive Hours Amends")
    effective_hours = fields.Float(string="Effective Hours", default=0)
    hide_approved_hours = fields.Boolean(
        compute="_compute_hide_approved_hours",
        string="Effective Hours Access",
    )
    team_leader_approval = fields.Boolean(
        compute="_compute_team_leader_approval",
        string="Lead Engineer",
        # store=True
    )
    consulting_hours = fields.Many2one(related="task_id.task_type_id", store=True, string="Consulting Hours")
    last_approver_id = fields.Many2one('res.users', string="Last Approver")
    hide_timesheet_approve_btn= fields.Boolean(compute="_compute_hide_timesheet_approve_btn")
    show_timesheet_reset_btn= fields.Boolean(compute="_compute_hide_timesheet_approve_btn")
    is_approved = fields.Boolean(help="Becomes True when timesheet approved for first time")
    productivity = fields.Float(string="Productivity(%)", compute="_compute_productivity", store=True, aggregator="avg")
    efficiency = fields.Float(string="Efficiency(%)", compute="_compute_efficiency", store=True, aggregator="avg")
    utilization_rate = fields.Float(string="Utilization Rate(%)", compute="_compute_utilization", store=True, aggregator="avg")
    status = fields.Selection([
        ('on_time', 'On Time'),
        ('late', 'Late')
    ], string='Status', compute='_compute_status', store=True, readonly=False)

    @api.depends('date')
    def _compute_status(self):
        """ Mark status as late when it exceeds 3 days excluding weekend and public holiday  """
        for line in self:
            if not line.date or not line.create_date:
                line.status = 'on_time'
                continue
            today = line.create_date.date()
            entry_date = line.date
            holiday_list = line.employee_id.holiday_list_id
            # Count working days (exclude weekends and public holidays)
            working_days = 0
            current_day = entry_date
            while current_day < today:
                if current_day.weekday() < 5:  # Not Saturday/Sunday
                    is_holiday = line.employee_id.is_holiday(current_day, holiday_list)
                    if not is_holiday:
                        working_days += 1
                current_day += timedelta(days=1)
            line.status = 'late' if working_days > 3 else 'on_time'

    @api.depends("approved_hours", "unit_amount")
    def _compute_productivity(self):
        for rec in self:
            rec.productivity = (rec.approved_hours / rec.unit_amount) if rec.approved_hours else 0.0

    @api.depends("effective_hours", "unit_amount")
    def _compute_efficiency(self):
        for rec in self:
            rec.efficiency = (rec.effective_hours/rec.unit_amount) if rec.effective_hours else 0.0


    @api.depends("effective_hours", "approved_hours")
    def _compute_utilization(self):
        for rec in self:
            rec.utilization_rate = (rec.approved_hours/rec.effective_hours) if rec.effective_hours else 0.0

    @api.model
    def get_view(self, view_id=None, view_type='list', **kwargs):
        res = super().get_view(view_id, view_type, **kwargs)
        if view_type == 'list':
            user = self.env['res.users'].browse(self.env.context.get('uid', False))
            restricted_groups = user._get_restricted_group()
            
            if user.has_group("project.group_project_user") and not any(user.has_group(group) for group in restricted_groups):
                doc = etree.XML(res['arch'])
                for node in doc.xpath("//field[@name='effective_hours']"):
                    node.set("readonly", "1")
                res['arch'] = etree.tostring(doc, encoding='unicode')
            else:
                doc = etree.XML(res['arch'])
                for node in doc.xpath("//field[@name='effective_hours']"):
                    node.set("readonly", "0")
                res['arch'] = etree.tostring(doc, encoding='unicode')
                
        return res

    def _compute_hide_approved_hours(self):
        for timesheet in self:
            timesheet.hide_approved_hours = False

            user_groups = set(self.env.user.group_ids.get_external_id().values())
            restricted_groups = set(self.env.user._get_restricted_manager_group())

            if self.env.user.id != self.env.ref("base.user_admin").id:
                if not restricted_groups.intersection(user_groups):
                    timesheet.hide_approved_hours = True

    def _compute_team_leader_approval(self):
        for timesheet in self:
            timesheet.team_leader_approval = False
            has_my_group = self.env.user.has_group('aktiv_pms.group_aktiv_project_manager') or self.env.user.has_group('aktiv_pms.group_aktiv_project_team_leader')
            if self.env.ref("base.user_admin").id != self.env.user.id:
                if not has_my_group:
                    timesheet.team_leader_approval = True

    def update_user_type(self, vals):
        if "employee_id" in vals:
            employee = self.env["hr.employee"].browse(vals["employee_id"])
            user_id = employee.user_id

            if user_id:
                user_groups = set(v for v in user_id.group_ids.get_external_id().values() if v)
                restricted_groups = user_id._get_restricted_group()

                if "project.group_project_user" in user_groups:
                    if not any(group in user_groups for group in restricted_groups):
                        if "aktiv_pms.group_aktiv_project_QA" in user_groups:
                            vals.update({"user_type": "qa"})
                        else:
                            vals.update({"user_type": "dev"})

        return vals


    def _log_approved_hours(self, new_hour, new_reason, is_self_amends):
        self.ensure_one()
        getHtmlValue = lambda v, t: self.env['ir.qweb.field.%s' % t].value_to_html(v, {})
        logs = json.loads(self.approved_hours_logs or "[]")
        logs.append({
                'old_hour': getHtmlValue(self.approved_hours, 'float_time'),
                'new_hour': getHtmlValue(new_hour, 'float_time'),
                'datetime': getHtmlValue(fields.Datetime.now(), 'datetime'),
                'isokay': (self.approved_hours < new_hour),
                'employee': self.env.user.employee_id.name,
                'reason': "Self Amends" if is_self_amends else (new_reason or ""),
            })
        return json.dumps(logs)

    def _get_lock_days(self):
        """ Retrieves the timesheet locking period (in days) from config, safely returns 0 if unset or invalid. """
        param = self.env['ir.config_parameter'].sudo().get_param('aktiv_pms.timesheet_locking_period')
        try:
            return int(param or 0)
        except ValueError:
            return 0

    def _check_lock_date(self, date=None):
        """ Prevents non-project managers from logging timesheets before the lock period cutoff date."""
        if (self.env.user.has_group('project.group_project_manager') or
            self.env.user.has_group('aktiv_pms.group_allow_edit_old_timesheets')):
            return
        lock_days = self._get_lock_days()
        if lock_days <= 0:
            return
        today = fields.Date.today()
        # to exclude weekends
        working_days_count = 0
        temp_day = today
        while working_days_count < lock_days:
            temp_day -= timedelta(days=1)
            if temp_day.weekday() < 5:
                working_days_count += 1

        cutoff_date = temp_day
        check_date = Date.to_date(date) or self.date
        if check_date < cutoff_date:
            raise ValidationError(_("Timesheet Entry is locked for this Date"))

    @api.model_create_multi
    def create(self, vals_list):
        # Enforces date lock check for non-project managers before allowing timesheet changes.
        if not self.env.user.has_group('project.group_project_manager'):
            for vals in vals_list:
                self._check_lock_date(vals.get('date'))
        vals_list = [self.update_user_type(vals) for vals in vals_list]
        records = super(AccountAnalyticLine, self).create(vals_list)
        records._compute_status()
        return records

    def write(self, vals):
        """Method Override to update state when timesheet entries are updated"""
        # Enforces date lock check for non-project managers before allowing timesheet changes.
        allowed_fields_when_locked = {'effective_hours', 'approved_hours', 'remaining_hours'}
        editing_only_allowed_fields = set(vals.keys()).issubset(allowed_fields_when_locked)
        if not self.env.user.has_group('project.group_project_manager') and not self.env.context.get('skip_lock_check') and not editing_only_allowed_fields:
            self._check_lock_date(vals.get('date'))
        for line in self:
            if any(field in vals for field in allowed_fields_when_locked):
                line._check_approval_lock_date()

            # Log approved hours history

            if ('approved_hours' in vals and vals.get('approved_hours') != self.approved_hours  and vals.get('state') != 'approval' or\
                    vals.get('last_approval_reason', "")
            ):
                vals.update(
                    approved_hours_logs=line._log_approved_hours(
                            vals.get('approved_hours', 0),
                            vals.get('last_approval_reason'),
                            (line.employee_id.id == self.env.user.employee_id.id)
                        )
                    )
        vals = self.update_user_type(vals)
        if self.data_sync == 'sync' and (vals.get("date") or vals.get("name")
                                         or 'effective_hours' in vals or 'approved_hours' in vals
                                         or 'unit_amount' in vals or vals.get("project_id") or vals.get("task_id")):
            vals.update({"data_sync": "not_sync"})
        return super(AccountAnalyticLine, self).write(vals)

    # Call Compute QA Timesheet Boolean True
    @api.depends("user_id", "employee_id")
    def _compute_qa_timesheet(self):
        for employee in self:
            employee.qa_timesheet = False
            if (
                    self.env.user.has_group("aktiv_pms.group_aktiv_project_QA")
                    or employee.user_id.id == self.env.uid
            ):
                employee.qa_timesheet = True

    from odoo.exceptions import UserError, ValidationError

    def unlink(self):
        # Check if the current user has permission to delete timesheets
        user = self.env.user
        restricted_groups = user._get_restricted_group()
        
        if (
            user.has_group('project.group_project_user')
            and not any(user.has_group(group) for group in restricted_groups)
        ):
            raise UserError(_('You are not allowed to delete the Timesheet!'))

        # Delete related timesheet entries on PM tool
        for rec in self:
            if rec.task_id and rec.pmtool_timesheet_id:
                odoo = get_connection(self.env)
                if odoo:
                    try:
                        pm_ts = odoo.env["account.analytic.line"].browse(int(rec.pmtool_timesheet_id))
                        if pm_ts:
                            pm_ts.unlink()
                    except Exception:
                        return super().unlink()
                else:
                    raise ValidationError("Please establish connection with PM tool database!")

        return super().unlink()


    @api.onchange("unit_amount")
    def onchange_unit_amount(self):
        if self.project_id.allow_effective_as_invested_hours:
            self.effective_hours = self.unit_amount

    @api.model
    def bulk_timesheet_approved(self):
        self.timesheet_approved()

    def has_project_access(self):
        """
        Check if the user has access to the project based on their role and permissions.

        :return: True if the user has access, False otherwise.
        :rtype: bool
        """
        user = self.env.user
        project = self.project_id

        if user.id in project.team_leader_ids.ids and user.has_group('aktiv_pms.group_aktiv_project_team_leader'):
            return True
        if user.id in project.user_id.ids and (user.has_group('aktiv_pms.group_aktiv_project_manager') or user.has_group('project.group_project_manager')):
            return True
        if user.id in project.consultant_ids.ids and user.has_group('aktiv_pms.group_aktiv_project_functional'):
            return True
        return False

    def _compute_hide_timesheet_approve_btn(self):
        for rec in self:
            if rec.state == 'approved' and not rec.has_project_access():
                rec.hide_timesheet_approve_btn = True
                rec.show_timesheet_reset_btn = False
            elif rec.state != 'approved' and not rec.has_project_access():
                rec.hide_timesheet_approve_btn = True
                rec.show_timesheet_reset_btn = False
            elif rec.state == 'approved' and rec.has_project_access():
                rec.hide_timesheet_approve_btn = True
                rec.show_timesheet_reset_btn = True
            elif rec.state != 'approved' and rec.has_project_access():
                rec.hide_timesheet_approve_btn = False
                rec.show_timesheet_reset_btn = False
            else:
                rec.hide_timesheet_approve_btn = True
                rec.show_timesheet_reset_btn = False

    def _check_approval_lock_date(self):
        """
        Lock approval for previous month's timesheets after the 3 working days of the current month.
        Approval is always allowed for current and future dates.
        """
        if (self.env.user.has_group('project.group_project_manager') or
            self.env.user.has_group('aktiv_pms.group_allow_approve_old_timesheets')):
            return
        today = fields.Date.today()
        current_month_start = today.replace(day=1)
        # Calculate the first 3 working days of the current month
        working_days = []
        temp_day = current_month_start
        while len(working_days) < 3:
            if temp_day.weekday() < 5:
                working_days.append(temp_day)
            temp_day += timedelta(days=1)
        last_allowed_date = working_days[-1]
        # Determine previous month and year
        prev_month = (today.month - 1) or 12
        prev_month_year = today.year if today.month != 1 else today.year - 1
        for rec in self:
            check_date = fields.Date.to_date(rec.date)
            # Allow current month and future dates always
            if check_date >= current_month_start:
                continue
            # Allow approval for previous month only if today is within first 3 working days
            if today <= last_allowed_date:
                if check_date.year == prev_month_year and check_date.month == prev_month:
                    continue
                else:
                    raise ValidationError(
                        _("You cannot Approve/Reset/Edit Hours of timesheets for this Date."))

            raise ValidationError(_("You cannot Approve/Reset/Edit Hours of timesheets for this Date."))

    def timesheet_approved(self):
        """Open wizard when project functional approves timesheet for the second time"""
        self._check_approval_lock_date()
        approved_with_remaining = self.filtered(
            lambda l: l.state == 'approved' and l.remaining_hours > 0
        )
        if approved_with_remaining:
            dates = '\n'.join(
                '• %s | %s | %s | %s' % (
                    r.date,
                    r.employee_id.name,
                    r.project_id.name or '-',
                    r.task_id.name or '-',
                )
                for r in approved_with_remaining
            )
            raise ValidationError(
                _("The following entries are already Approved and have Remaining Hours set.\n"
                  "Please Reset them first before approving again:\n\n%s") % dates
            )

        for rec in self:
            user = rec.env.user
            vals = {
                'approved_hours': rec.remaining_hours,
                'last_approver_id': user.id,
                'state': 'approved',
                'remaining_hours': 0,
            }
            if rec.is_approved:
                if rec.last_approver_id.id != user.id:
                    return {
                        "type": "ir.actions.act_window",
                        "name": "Reason for approval",
                        "view_type": "form",
                        "view_mode": "form",
                        "res_model": "account.analytic.line.wizard",
                        "target": "new",
                    }
            else:
                if not rec.has_project_access():
                    raise UserError("You are not allowed to approve Timesheet!")
                vals.update({
                    'is_approved': True,
                })

            rec.with_context(skip_lock_check=True).write(vals)

    def timesheet_reset(self):
        for rec in self:
            if not rec.has_project_access():
                raise UserError("You are not allowed to Reset Timesheet!")
            rec._check_approval_lock_date()
            rec.with_context(skip_lock_check=True).write({
                'state': 'approval',
                'remaining_hours': rec.approved_hours,
            })


    def timesheet_approve(self):
        """
        Dummy: as this method is previously defined
        and the logic were same as `timesheet_approved` due to this
        we have removed logic and simply called it.
        """
        self.timesheet_approved()

    @api.onchange('state')
    def onchange_state(self):
        for rec in self:
            if rec.state == 'approved':
                raise UserError(_('You need to click on approved button to approve hours'))
