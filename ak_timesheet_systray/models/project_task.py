from odoo import models
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from ...aktiv_pms.utils import get_connection

class ProjectTask(models.Model):
    _inherit = "project.task"

    def action_sync_timesheet_pm_tool(self, uid=None):
        """
            Syncs unsynced timesheets to a B2B PM tool using the timesheet widget systray.
        """
        uid = uid or self.env.uid
        print(uid, "UID")
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
        # tasks = unsync_timesheet.filtered(lambda timesheet : timesheet.task_id != False)


        # domain = ['|', '|', ('user_ids', 'in', user.id), ('code_reviewer_ids', 'in', user.id),
        #           ('task_qa_ids', 'in', user.id), ('pm_tool_tasks', '!=', False)]
        # tasks = self.env['project.task'].search(domain)
        if not tasks:
            return False
        task_ids = [int(rec.pm_tool_task_id) for rec in tasks]
        project_ids = odoo_conn.env["project.task"].search_read([("id", "in", task_ids)], fields=["id", "project_id"])
        project_id_map = {project['id']: project['project_id'][0] for project in project_ids}

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
                        "unit_amount": timesheet.unit_amount, "project_id": project_id, "employee_id": employee_id[0], }
                    pm_ts = odoo_conn.env["account.analytic.line"].browse(int(timesheet.pmtool_timesheet_id))
                    if pm_ts:
                        pm_ts.write(vals)
                    else:
                        timesheet_id = odoo_conn.env["account.analytic.line"].create(vals)
                        update_vals.update({"pmtool_timesheet_id": timesheet_id})
                    update_vals.update({"data_sync": "sync"})
                except Exception as e:
                    self._log_logging(e, "sync_timesheet_to_pm_tool", )
                    continue
                timesheet.write(update_vals)

        return True
