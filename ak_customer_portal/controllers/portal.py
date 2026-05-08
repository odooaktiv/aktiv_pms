from collections import OrderedDict
from operator import itemgetter

from dateutil.relativedelta import relativedelta
from odoo import SUPERUSER_ID, _, fields, http  # pylint: disable=E0401
from odoo.addons.hr_timesheet.controllers.portal import \
    TimesheetCustomerPortal  # pylint: disable=E0401
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager  # pylint: disable=E0401
from odoo.exceptions import AccessError, MissingError  # pylint: disable=E0401
from odoo.http import request  # pylint: disable=E0401
from odoo.tools import date_utils
from odoo.tools import groupby as groupbyelem  # pylint: disable=E0401


class TimesheetCustomerPortalCustom(TimesheetCustomerPortal):

    """Timesheet Customer Portal"""

    def _prepare_home_portal_values(self, counters):
        """Inherit method to changes timesheet counts: now sum of only current project
        timesheets will be displayed"""
        values = super(TimesheetCustomerPortalCustom, self)._prepare_home_portal_values(
            counters
        )
        total_timesheet_ids = self._get_project_timesheet_ids()
        domain = [("id", "in", total_timesheet_ids)]
        timesheet_sudo = request.env["account.analytic.line"].sudo()
        timesheet_count = timesheet_sudo.search_count(domain)
        values.update({"timesheet_count": timesheet_count})
        return values

    def _get_searchbar_sortings(self):
        """Inherit method to remove employee, project and description from sort by"""
        res = super(TimesheetCustomerPortalCustom, self)._get_searchbar_sortings()
        remove_elements_from_sort_by = ["employee", "name"]
        if not request.env.user.has_group("aktiv_pms.group_aktiv_project_manager"):
            remove_elements_from_sort_by.append("project")
        # "project",
        for element in remove_elements_from_sort_by:
            res.pop(element)
        return res

    def _get_searchbar_groupby(self):
        """Inherit method to remove employee and project from Group By"""
        res = super(TimesheetCustomerPortalCustom, self)._get_searchbar_groupby()
        remove_elements_from_group_by = ["employee"]
        if not request.env.user.has_group("aktiv_pms.group_aktiv_project_manager"):
            remove_elements_from_group_by.append("project")
        # , "project"
        for element in remove_elements_from_group_by:
            res.pop(element)
        return res

    def _get_searchbar_inputs(self):
        """Inherit method to remove employee and project from Search in all"""
        res = super(TimesheetCustomerPortalCustom, self)._get_searchbar_inputs()
        remove_elements_from_search_in_all = ["employee"]
        if not request.env.user.has_group("aktiv_pms.group_aktiv_project_manager"):
            remove_elements_from_search_in_all.append("project")
        # , "project"
        for element in remove_elements_from_search_in_all:
            res.pop(element)
        return res

    def _get_project_timesheet_ids(self):
        """return timesheet ids of tasks of current project of customer"""
        if request.env.user.partner_id.company_type == "company":
            partner_ids = (
                request.env.user.partner_id.child_ids.ids
                if request.env.user.partner_id.child_ids
                else [] + [request.env.user.partner_id.id]
            )
            domain_project = [("partner_id", "in", partner_ids)]
        elif request.env.user.partner_id and request.env.user.partner_id.parent_id and request.env.user.partner_id.parent_id.company_type == 'company':
            domain_project = ['|', ("partner_id", "=", request.env.user.partner_id.parent_id.id), ("partner_id", "=", request.env.user.partner_id.id)]
        else:
            domain_project = [("partner_id", "=", request.env.user.partner_id.id)]
        project_model = request.env["project.project"].sudo()

        stackholder_projects = project_model.search(
           [('project_owner_ids', 'in', request.env.user.id)]
        )

        # if project stokholder so display only his projects related to the project stackholder.
        # if user project manager so display all projects at portal level.
        if request.env.user.has_group("aktiv_pms.group_aktiv_project_manager") or request.env.user.id == SUPERUSER_ID:
            project = project_model.search([])
        elif stackholder_projects:
            project = stackholder_projects
        else:
            project = project_model.search(domain_project, limit=1)

        total_timesheet_ids = (
            project.task_ids.filtered(
                lambda l:(l.approved_hours > 0 or l.productive_hours_on_sub_task > 0)
            )
            .mapped("timesheet_ids")
            .filtered(
                lambda timesheet: timesheet.approved_hours > 0
                and timesheet.state == "approved"
            )
            .ids
            or []
        )
        return total_timesheet_ids

    @http.route(
        ["/my/timesheets", "/my/timesheets/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_timesheets(
        self,
        page=1,
        sortby=None,
        filterby=None,
        search=None,
        search_in="all",
        groupby="none",
        **kw
    ):
        Timesheet = request.env["account.analytic.line"]
        domain = Timesheet._timesheet_get_portal_domain()
        timesheet_sudo = Timesheet.sudo()

        values = self._prepare_portal_layout_values()
        _items_per_page = 100

        searchbar_sortings = self._get_searchbar_sortings()

        searchbar_inputs = self._get_searchbar_inputs()

        searchbar_groupby = self._get_searchbar_groupby()

        today = fields.Date.today()
        quarter_start, quarter_end = date_utils.get_quarter(today)
        last_week = today + relativedelta(weeks=-1)
        last_month = today + relativedelta(months=-1)
        last_year = today + relativedelta(years=-1)

        searchbar_filters = {
            "all": {"label": _("All"), "domain": []},
            "today": {"label": _("Today"), "domain": [("date", "=", today)]},
            "week": {
                "label": _("This week"),
                "domain": [
                    ("date", ">=", date_utils.start_of(today, "week")),
                    ("date", "<=", date_utils.end_of(today, "week")),
                ],
            },
            "month": {
                "label": _("This month"),
                "domain": [
                    ("date", ">=", date_utils.start_of(today, "month")),
                    ("date", "<=", date_utils.end_of(today, "month")),
                ],
            },
            "year": {
                "label": _("This year"),
                "domain": [
                    ("date", ">=", date_utils.start_of(today, "year")),
                    ("date", "<=", date_utils.end_of(today, "year")),
                ],
            },
            "quarter": {
                "label": _("This Quarter"),
                "domain": [("date", ">=", quarter_start), ("date", "<=", quarter_end)],
            },
            "last_week": {
                "label": _("Last week"),
                "domain": [
                    ("date", ">=", date_utils.start_of(last_week, "week")),
                    ("date", "<=", date_utils.end_of(last_week, "week")),
                ],
            },
            "last_month": {
                "label": _("Last month"),
                "domain": [
                    ("date", ">=", date_utils.start_of(last_month, "month")),
                    ("date", "<=", date_utils.end_of(last_month, "month")),
                ],
            },
            "last_year": {
                "label": _("Last year"),
                "domain": [
                    ("date", ">=", date_utils.start_of(last_year, "year")),
                    ("date", "<=", date_utils.end_of(last_year, "year")),
                ],
            },
        }
        # default sort by value
        if not sortby:
            sortby = "date"
        order = searchbar_sortings[sortby]["order"]
        # default filter by value
        if not filterby:
            filterby = "all"
        # customization starts ---------->
        domain = [
            (
                "id",
                "in",
                self._get_project_timesheet_ids(),
            )
        ]
        domain += searchbar_filters[filterby]["domain"]
        if search and search_in:
            domain += self._get_search_domain(search_in, search)

        timesheet_count = timesheet_sudo.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/timesheets",
            url_args={
                "sortby": sortby,
                "search_in": search_in,
                "search": search,
                "filterby": filterby,
                "groupby": groupby,
            },
            total=timesheet_count,
            page=page,
            step=_items_per_page,
        )
        # get current project timesheet ids and update it in domain: so only those
        # timesheets will be displayed on portal level /my/timesheets

        def get_timesheets():
            groupby_mapping = self._get_groupby_mapping()
            field = groupby_mapping.get(groupby, None)
            orderby = "%s, %s" % (field, order) if field else order

            current_project_timesheets = timesheet_sudo.search(
                domain,  # Use update domain to search for timesheets
                order=orderby,
                limit=_items_per_page,
                offset=pager["offset"],
            )

            if field:
                if groupby == "date":
                    raw_timesheets_group = timesheet_sudo.read_group(
                        domain,
                        ["approved_hours:sum", "ids:array_agg(id)"],
                        ["date:day"],
                    )
                    grouped_timesheets = [
                        (timesheet_sudo.browse(group["ids"]), group["approved_hours"])
                        for group in raw_timesheets_group
                    ]

                else:
                    time_data = timesheet_sudo.read_group(
                        domain, [field, "approved_hours:sum"], [field]
                    )
                    mapped_time = dict(
                        [
                            (m[field][0] if m[field] else False, m["approved_hours"])
                            for m in time_data
                        ]
                    )
                    grouped_timesheets = [
                        (timesheet_sudo.concat(*g), mapped_time[k.id])
                        for k, g in groupbyelem(
                            current_project_timesheets, itemgetter(field)
                        )
                    ]
                return current_project_timesheets, grouped_timesheets

            grouped_current_project_timesheets = (
                [
                    (
                        current_project_timesheets,
                        sum(current_project_timesheets.mapped("approved_hours")),
                    )
                ]
                if current_project_timesheets
                else []
            )
            return current_project_timesheets, grouped_current_project_timesheets
            # customization ends ---------->

        timesheets, grouped_timesheets = get_timesheets()

        values.update(
            {
                "timesheets": timesheets,
                "grouped_timesheets": grouped_timesheets,
                "page_name": "timesheet",
                "default_url": "/my/timesheets",
                "pager": pager,
                "searchbar_sortings": searchbar_sortings,
                "search_in": search_in,
                "search": search,
                "sortby": sortby,
                "groupby": groupby,
                "searchbar_inputs": searchbar_inputs,
                "searchbar_groupby": searchbar_groupby,
                "searchbar_filters": OrderedDict(sorted(searchbar_filters.items())),
                "filterby": filterby,
                "is_uom_day": request.env[
                    "account.analytic.line"
                ]._is_timesheet_encode_uom_day(),
                "from_my_timesheet": True,
            }
        )
        return request.render("hr_timesheet.portal_my_timesheets", values)


class ProjectCustomerPortal(CustomerPortal):

    """Project Customer Portal"""

    def _prepare_home_portal_values(self, counters):
        values = super(ProjectCustomerPortal, self)._prepare_home_portal_values(counters)
        if request.env.user.partner_id and request.env.user.partner_id.parent_id and request.env.user.partner_id.parent_id.company_type == 'company':
            domain_project = ['|', ("partner_id", "=", request.env.user.partner_id.parent_id.id), ("partner_id", "=", request.env.user.partner_id.id)]
        else:
            domain_project = [("partner_id", "=", request.env.user.partner_id.id)]
        if "project_count" in counters:
            # currently only one project is displayed so set count of project to 1 even
            # if more than one project found for same customer
            customer_projects_count = (
                request.env["project.project"]
                .sudo()
                .search_count(domain_project)
            )
            if customer_projects_count > 0:
                values["project_count"] = 1
            else:
                values["project_count"] = 0
        if "task_count" in counters:
            values["task_count"] = (
                request.env["project.task"]
                .sudo()
                .search_count(domain_project)
            )
        return values

    def _project_get_page_view_values(self, project, access_token, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', groupby=None, **kwargs):
        # default filter by value
        domain = [('project_id', '=', project.id), ("parent_id", "=", False),]
        # pager
        url = "/my/projects/%s" % project.id
        values = self._prepare_tasks_values(page, date_begin, date_end, sortby, search, search_in, groupby, url, domain, su=bool(access_token), project=project)
        # adding the access_token to the pager's url args,
        # so we are not prompted for loging when switching pages
        # if access_token is None, the arg is not present in the URL
        values['pager']['url_args']['access_token'] = access_token
        pager = portal_pager(**values['pager'])

        values.update(
            grouped_tasks=values['grouped_tasks'](pager['offset']),
            page_name='project',
            pager=pager,
            project=project,
            task_url=f'projects/{project.id}/task',
            preview_object=project,
        )

        if not groupby:
            values['groupby'] = 'project' if self._display_project_groupby(project) else 'none'

        return self._get_page_view_values(project, access_token, values, 'my_projects_history', False, **kwargs)

    # def _project_get_page_view_values(
    #     self,
    #     project,
    #     access_token,
    #     page=1,
    #     date_begin=None,
    #     date_end=None,
    #     sortby=None,
    #     search=None,
    #     search_in="content",
    #     groupby=None,
    #     **kwargs
    # ):
    #     """Override method: To add domain of task type as customization
    #     and search tasks using sudo"""
    #     # TODO: refactor this because most of this code is duplicated
    #     # from portal_my_tasks method
    #     values = self._prepare_portal_layout_values()
    #     searchbar_sortings = self._task_get_searchbar_sortings()

    #     searchbar_inputs = self._task_get_searchbar_inputs()
    #     searchbar_groupby = self._task_get_searchbar_groupby()

    #     # default sort by value
    #     if not sortby:
    #         sortby = "date"
    #     order = searchbar_sortings[sortby]["order"]
    #     # default filter by value # added custom domain of task type
    #     domain = [
    #         ("project_id", "=", project.id),
    #         ("parent_id", "=", False),
    #     ]
    #     # default group by value
    #     if not groupby:
    #         groupby = "project"

    #     if date_begin and date_end:
    #         domain += [
    #             ("create_date", ">", date_begin),
    #             ("create_date", "<=", date_end),
    #         ]
    #     # search
    #     if search and search_in:
    #         domain += self._task_get_search_domain(search_in, search)
    #     task_model = request.env["project.task"].sudo()
    #     # task count
    #     task_count = task_model.search_count(domain)
    #     # pager
    #     url = "/my/project/%s" % project.id
    #     pager = portal_pager(
    #         url=url,
    #         url_args={
    #             "date_begin": date_begin,
    #             "date_end": date_end,
    #             "sortby": sortby,
    #             "groupby": groupby,
    #             "search_in": search_in,
    #             "search": search,
    #         },
    #         total=task_count,
    #         page=page,
    #         step=self._items_per_page,
    #     )
    #     # content according to pager and archive selected
    #     order = self._task_get_order(order, groupby)
    #     tasks = task_model.search(
    #         domain, order=order, limit=self._items_per_page, offset=pager["offset"]
    #     )
    #     request.session["my_project_tasks_history"] = tasks.ids[:100]
    #     groupby_mapping = self._task_get_groupby_mapping()
    #     group = groupby_mapping.get(groupby)
    #     if group:
    #         grouped_tasks = [
    #             task_model.concat(*g) for k, g in groupbyelem(tasks, itemgetter(group))
    #         ]
    #     else:
    #         grouped_tasks = [tasks]

    #     values.update(
    #         date=date_begin,
    #         date_end=date_end,
    #         grouped_tasks=grouped_tasks,
    #         page_name="project",
    #         default_url=url,
    #         pager=pager,
    #         searchbar_sortings=searchbar_sortings,
    #         searchbar_groupby=searchbar_groupby,
    #         searchbar_inputs=searchbar_inputs,
    #         search_in=search_in,
    #         search=search,
    #         sortby=sortby,
    #         groupby=groupby,
    #         project=project,
    #     )
    #     return self._get_page_view_values(
    #         project, access_token, values, "my_projects_history", False, **kwargs
    #     )

    @http.route("/project/task/<int:task_id>", type="jsonrpc", website=True, auth="user")
    def portal_project_task(self, task_id, **post):  # pylint: disable=W0613
        """Search for timesheets of task, of approved state and approved
        hours greater than zero"""
        task_id = request.env["project.task"].sudo().browse(task_id)
        timesheets = (
            request.env["account.analytic.line"]
            .sudo()
            .search(
                [
                    ("task_id", "=", task_id.id),
                    ("state", "=", "approved"),
                    ("approved_hours", ">", 0),
                ]
            )
        )
        total = 0.0
        for rec in timesheets:
            total += rec.approved_hours
        vals = {
            "total_hours": "{0:02.0f}:{1:02.0f}".format(*divmod(float(total) * 60, 60)),
            "task": task_id,
            "timesheets": timesheets,
            "no_header_footer": True,
            "task_url": "project/%s/task" % task_id.project_id.id,
        }
        return request.env["ir.ui.view"]._render_template(
            "ak_customer_portal.task_modal", vals
        )

    @http.route(
        ["/aktiv_pms/task/report/<model('project.task'):task>"],
        type="http",
        auth="user",
        website=True,
    )
    def print_timesheet(self, task, **kw):  # pylint: disable=W0613
        """method to print timesheet"""
        pdf, _ = (
            request.env.ref("hr_timesheet.timesheet_report_task")
            .with_context(check_move_validity=True)
            .sudo()
            ._render_qweb_pdf([task.sudo().id])
        )
        pdfhttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", "%s" % len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

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

    @http.route(
        ["/my/projects", "/my/projects/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_projects(
        self,
        page=1,
        date_begin=None,
        date_end=None,
        sortby=None,
        **kw  # pylint: disable=W0613
    ):
        """overridde method"""
        values = self._prepare_portal_layout_values()
        project_model = request.env["project.project"].sudo()
        if request.env.user.partner_id.company_type == "company":
            partner_ids = (
                request.env.user.partner_id.child_ids.ids
                if request.env.user.partner_id.child_ids
                else [] + [request.env.user.partner_id.id]
            )
            domain = [("partner_id", "in", partner_ids)]
        elif request.env.user.partner_id and request.env.user.partner_id.parent_id and request.env.user.partner_id.parent_id.company_type == 'company':
            domain = ['|', ("partner_id", "=", request.env.user.partner_id.parent_id.id), ("partner_id", "=", request.env.user.partner_id.id)]
        else:
            domain = [("partner_id", "=", request.env.user.partner_id.id)]

        searchbar_sortings = {
            "date": {"label": _("Newest"), "order": "create_date desc"},
            "name": {"label": _("Name"), "order": "name"},
        }
        if not sortby:
            sortby = "date"
        order = searchbar_sortings[sortby]["order"]

        if date_begin and date_end:
            domain += [
                ("create_date", ">", date_begin),
                ("create_date", "<=", date_end),
            ]

        # projects count
        project_count = project_model.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/projects",
            url_args={"date_begin": date_begin, "date_end": date_end, "sortby": sortby},
            total=project_count,
            page=page,
            step=self._items_per_page,
        )
        # content according to pager and archive selected

        stackholder_projects = project_model.search(
           [('project_owner_ids', 'in', request.env.user.id)]
        )

        # if project stokholder so display only his projects related to the project stackholder.
        # if user project manager so display all projects at portal level.
        if request.env.user.has_group("aktiv_pms.group_aktiv_project_manager") or request.env.user.id == SUPERUSER_ID:
            projects = project_model.search(
               [], order=order, offset=pager["offset"]
            )
        elif stackholder_projects:
            projects = stackholder_projects
        else:
            projects = project_model.search(
                domain, order=order, limit=1, offset=pager["offset"]
            )

        task_states = self._get_task_stages(projects)

        # Extract counts for different states
        task_in_progress_count = len(task_states.get("development")) or 0
        task_delivered_count = len(task_states.get("customer_review")) or 0
        task_done_count = len(task_states.get("done")) or  0
        task_in_planning_count = len(task_states.get("new")) or 0

        request.session["my_projects_history"] = projects.ids[:100]
        timesheet_model = request.env["account.analytic.line"]
        domain = timesheet_model._timesheet_get_portal_domain()
        values.update(
            {
                "date": date_begin,
                "date_end": date_end,
                "projects": projects,
                "page_name": "project",
                "default_url": "/my/projects",
                "pager": pager,
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
                "task_in_progress": task_in_progress_count,
                "task_delivered": task_delivered_count,
                "task_done": task_done_count,
                "task_in_planning": task_in_planning_count,
                "timesheet_count": timesheet_model.sudo().search_count(domain),
                "from_project_list": True,
                "project_count" : project_count,
            }
        )

        return request.render("project.portal_my_projects", values)


    @http.route(
        ["/my/projects/<int:project_id>"], type="http", auth="public", website=True
    )
    def portal_my_project(
        self,
        project_id=None,
        access_token=None,
        page=1,
        date_begin=None,
        date_end=None,
        sortby=None,
        search=None,
        search_in="content",
        groupby=None,
        **kw  # pylint: disable=W0613
    ):
        """Override controller in portal task list template"""
        try:
            project_sudo = self._document_check_access(
                "project.project", project_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")
        # if project_sudo.with_user(request.env.user)._check_project_sharing_access():
        #     return request.render(
        #         "project.project_sharing_portal", {"project_id": project_id}
        #     )
        project_sudo = (
            project_sudo if access_token else project_sudo.with_user(request.env.user)
        )
        values = self._project_get_page_view_values(
            project_sudo,
            access_token,
            page,
            date_begin,
            date_end,
            sortby,
            search,
            search_in,
            groupby,
            **kw
        )
        values["task_url"] = "project/%s/task" % project_id
        project_id = request.env["project.project"].sudo().browse(project_id)

        task_states = self._get_task_stages(project_id)

        # Filter tasks based on states for customization tasks
        task_in_progress = task_states.get("development")
        task_in_planning = task_states.get("new")
        task_in_done = task_states.get("done")
        task_in_customer_review = task_states.get("customer_review")

        # Extract counts for different states
        group_task_in_progress_count = len(task_states.get("development")) or 0
        group_task_cust_review_count = len(task_states.get("customer_review")) or 0
        group_task_done_count = len(task_states.get("done")) or  0
        group_task_new_count = len(task_states.get("new")) or 0

        values.update(
            {
                "group_task_in_progress": task_in_progress,
                "group_task_in_planning": task_in_planning,
                "group_task_in_customer_review": task_in_customer_review,
                "group_task_in_done": task_in_done,
                "group_task_in_progress_count": group_task_in_progress_count,
                "group_task_cust_review_count": group_task_cust_review_count,
                "group_task_done_count": group_task_done_count,
                "group_task_new_count": group_task_new_count,
                "from_task_list": True,
            }
        )

        return request.render("project.portal_my_project", values)

    @http.route(
        "/project/sub_task/<int:task_id>", type="jsonrpc", website=True, auth="user"
    )
    def portal_project_sub_task(self, task_id, **post):  # pylint: disable=W0613
        """Display list of sub-tasks"""
        task_id = request.env["project.task"].browse(task_id)
        vals = {
            "task": task_id,
            "no_header_footer": True,
            "task_url": "project/%s/task" % task_id.project_id.id,
        }
        return request.env["ir.ui.view"]._render_template(
            "ak_customer_portal.sub_task_modal", vals
        )
