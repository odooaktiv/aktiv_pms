from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = "project.task"

    is_sop_bank = fields.Boolean(related="project_id.is_sop_bank", store=True)
    old_db_id = fields.Integer(string="Old DB ID", copy=False)

    def _ensure_personal_stages(self):
        if self.env.context.get('sop_bank', False):
            pass
        else:
            user = self.env.user
            ProjectTaskTypeSudo = self.env['project.task.type'].sudo()
            # In the case no stages have been found, we create the default stages for the user
            if not ProjectTaskTypeSudo.search_count([('user_id', '=', user.id)], limit=1):
                ProjectTaskTypeSudo.with_context(lang=user.lang, default_project_id=False).create(
                    self.with_context(lang=user.lang)._get_default_personal_stage_create_vals(user.id)
                )

    @api.model
    def _get_default_personal_stage_create_vals(self, user_id):
        return []

    def _populate_missing_personal_stages(self):
        # Assign the default personal stage for those that are missing
        pass

    @api.model_create_multi
    def create(self, vals_list):
        context = self.env.context
        fields = vals_list[0].keys()
        if context.get('sop_bank', False) and 'project_id' not in fields:
            for val in vals_list:
                val['project_id'] = self.env.ref('ak_project_todo.project_sop_bank').id
            self = self.sudo()
        return super().create(vals_list)

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        """
        Override the read_group method to customize the behavior of grouping tasks by personal stage type.

        This method extends the default read_group behavior to handle grouping by the personal_stage_type_id field.
        If the first groupby field is 'personal_stage_type_id', it searches for the stages and groups the tasks
        accordingly, ensuring that tasks without any stage are also included in the results.

        """
        context = self.env.context
        if context.get('sop_bank', False):
            if groupby and groupby[0] == "stage_id" and (len(groupby) == 1 or lazy):
                stages = self.env["project.task.type"].search([('sop_stage', '=', True)])
                if stages:
                    # if the user has some stages
                    result = []
                    for stage in stages:
                        # notes by stage for stages user
                        nb_stage_counts = self.search_count(
                            domain + [("stage_id", "=", stage.id)]
                        )
                        result.append(
                            {
                                "__context": {"group_by": groupby[1:]},
                                "__domain": domain + [("stage_id.id", "=", stage.id)],
                                "stage_id": (stage.id, stage.name),
                                "stage_id_count": nb_stage_counts,
                                "__count": nb_stage_counts,
                                "__fold": stage.fold,
                            }
                        )
                    # note without user's stage
                    nb_notes_ws = self.search_count(
                        domain + [("stage_id", "not in", stages.ids)]
                    )
                    if nb_notes_ws:
                        # add note to the first column if it's the first stage
                        dom_not_in = ("stage_id", "not in", stages.ids)
                        if result and result[0]["stage_id"][0] == stages[0].id:
                            dom_in = result[0]["__domain"].pop()
                            result[0]["__domain"] = domain + ["|", dom_in, dom_not_in]
                            result[0]["stage_id_count"] += nb_notes_ws
                            result[0]["__count"] += nb_notes_ws
                        else:
                            # add the first stage column
                            result = [
                                {
                                    "__context": {"group_by": groupby[1:]},
                                    "__domain": domain + [],
                                    "stage_id": (stages[0].id, stages[0].name),
                                    "stage_id_count": nb_notes_ws,
                                    "__count": nb_notes_ws,
                                    "__fold": stages[0].name,
                                }
                            ] + result
                else:  # if stage_ids is empty, get note without user's stage
                    nb_notes_ws = self.search_count(domain)
                    if nb_notes_ws:
                        result = [
                            {  # notes for unknown stage
                                "__context": {"group_by": groupby[1:]},
                                "__domain": domain,
                                "stage_id": False,
                                "stage_id_count": nb_notes_ws,
                                "__count": nb_notes_ws,
                            }
                        ]
                    else:
                        result = []
                return result
        return super(ProjectTask, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
