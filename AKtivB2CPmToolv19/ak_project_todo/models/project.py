from odoo import api, fields, models


class ProjectProject(models.Model):
	_inherit="project.project"

	is_sop_bank = fields.Boolean(string="SOP Bank", store=True)
