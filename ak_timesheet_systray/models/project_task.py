from odoo import models
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from ...aktiv_pms.utils import get_connection

class ProjectTask(models.Model):
    _inherit = "project.task"

    def action_sync_timesheet_pm_tool(self, uid=None):
        """Sync the user's unsynced timesheets to the B2B PM tool.

        Triggered from the timesheet systray widget's "Sync" button. Pushes
        every ``account.analytic.line`` of the given user that is still
        ``data_sync == 'not_sync'`` and whose task is mapped to the PM tool
        (``pm_tool_task_id`` set) to the remote Odoo instance over odoorpc.

        For each timesheet:
            - if a remote line already exists (``pmtool_timesheet_id`` set),
              it is updated;
            - otherwise a new remote line is created and its id is stored
              back in ``pmtool_timesheet_id``.
        On success the local line is marked ``data_sync == 'sync'`` using
        ``skip_lock_check`` so the sync is never blocked by the timesheet
        date-lock. Any per-timesheet failure is logged and skipped so one bad
        entry does not abort the whole run.

        :param int uid: id of the user whose timesheets are synced. Defaults
            to the current user (``self.env.uid``). Passed explicitly by the
            widget so the sync runs for the logged-in user.
        :return: ``True`` when the run completed, ``False`` when it could not
            start (no PM-tool connection, unknown remote user/employee, or no
            eligible timesheets/tasks).
        :rtype: bool
        """
        uid = uid or self.env.uid
        try:
            odoo_conn = get_connection(self.env)
        except Exception as e:
            self._log_logging(e, "sync_timesheet_to_pm_tool", )
            return False
        if not odoo_conn:
            return False
        user = self.env['res.users'].browse(uid)
        user_id = odoo_conn.env["res.users"].search([("login", "=", user.user_name)])
        if not user_id:
            return False

        employee_id = odoo_conn.env["hr.employee"].search([("user_id", "in", user_id)])
        if not employee_id:
            self._log_logging("Employee for userID:%s not found on PM Tool!" % (user_id), "sync_timesheet_to_pm_tool", )
            return False
        unsync_timesheet = self.env['account.analytic.line'].search([('user_id', '=', user.id),
                                                                     ('data_sync', '=',  "not_sync"),
                                                                     ('task_id', '!=', False)])
        tasks = unsync_timesheet.mapped('task_id').filtered(lambda task: task.pm_tool_task_id != False)
        if not tasks:
            return False
        task_ids = [int(rec.pm_tool_task_id) for rec in tasks]
        project_ids = odoo_conn.env["project.task"].search_read([("id", "in", task_ids)], fields=["id", "project_id"])
        project_id_map = {project['id']: project['project_id'][0] for project in project_ids if project['project_id']}

        for rec in tasks:
            project_id = project_id_map.get(int(rec.pm_tool_task_id))
            if not project_id:
                self._log_logging("Project for task [%s] not found on PM Tool! " % (rec.name),
                    "sync_timesheet_to_pm_tool", )
                continue

            timesheets_to_sync = rec.timesheet_ids.filtered(lambda
                t: t.data_sync == "not_sync" and t.employee_id.user_id.user_name == user.user_name and t.date.year >= 2024 and t.date.month >= 3)

            for timesheet in timesheets_to_sync:
                date = timesheet.date.strftime("%Y-%m-%d")
                update_vals = {}
                try:
                    vals = {"task_id": int(rec.pm_tool_task_id), "date": date, "name": timesheet.name,
                            "unit_amount": timesheet.unit_amount, "effective_hours": timesheet.effective_hours,
                            "productive_hours": timesheet.approved_hours, "project_id": project_id,
                            "employee_id": employee_id[0], }
                    pm_ts = odoo_conn.env["account.analytic.line"].browse(int(timesheet.pmtool_timesheet_id))
                    if pm_ts:
                        pm_ts.write(vals)
                    else:
                        timesheet_id = odoo_conn.env["account.analytic.line"].create(vals)
                        update_vals.update({"pmtool_timesheet_id": timesheet_id})
                    update_vals.update({"data_sync": "sync"})
                    timesheet.with_context(skip_lock_check=True).write(update_vals)
                except Exception as e:
                    self._log_logging(e, "sync_timesheet_to_pm_tool", )
                    continue

        return True
