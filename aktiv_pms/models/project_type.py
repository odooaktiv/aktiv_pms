# -*- coding: utf-8 -*-

import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Types shipped with the module: the code (not the name) is what other code and the
# customer portal key on, so these can be renamed but not deleted or re-coded.
CORE_PROJECT_TYPES = {
    "project_type_fixed_cost": "fixed_cost",
    "project_type_success_pack": "success_pack",
    "project_type_time_material": "time_material",
}


class ProjectType(models.Model):
    """Kind of commercial arrangement of a project (fixed cost, success pack, ...).

    A model, not a selection, so new types can be added from the UI later without
    touching the code."""

    _name = "project.type"
    _description = "Project Type"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True,
        copy=False,
        help="Short technical key (lowercase, e.g. fixed_cost). Code and the customer "
        "portal decide behaviour from this, so it cannot be changed on the standard types.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    project_count = fields.Integer(compute="_compute_project_count")

    _code_unique = models.Constraint(
        "UNIQUE(code)", "The code of a project type must be unique."
    )

    @api.model
    def _normalize_code(self, code):
        return re.sub(r"[^a-z0-9]+", "_", (code or "").strip().lower()).strip("_")

    def _core_records(self):
        """Records of ``self`` that are standard types shipped with the module."""
        data = self.env["ir.model.data"].sudo().search(
            [
                ("module", "=", "aktiv_pms"),
                ("model", "=", self._name),
                ("res_id", "in", self.ids),
                ("name", "in", list(CORE_PROJECT_TYPES)),
            ]
        )
        return self.browse(data.mapped("res_id"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code"):
                vals["code"] = self._normalize_code(vals["code"])
        return super().create(vals_list)

    def write(self, vals):
        if "code" in vals:
            vals = dict(vals, code=self._normalize_code(vals["code"]))
            core = self._core_records()
            if core and any(rec.code != vals["code"] for rec in core):
                raise UserError(
                    _("The code of the standard project types cannot be changed.")
                )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_core_types(self):
        if self._core_records():
            raise UserError(
                _("The standard project types cannot be deleted. Archive them instead.")
            )

    def _compute_project_count(self):
        counts = {
            ptype.id: count
            for ptype, count in self.env["project.project"]
            .with_context(active_test=False)
            ._read_group([("project_type_id", "in", self.ids)], ["project_type_id"], ["__count"])
        }
        for rec in self:
            rec.project_count = counts.get(rec.id, 0)
