from odoo import api, fields, models


class ProjectTags(models.Model):
	_inherit = "project.tags"

	is_sop_bank = fields.Boolean(string="SOP Bank")
	old_db_id = fields.Integer(string="Old DB ID", copy=False)

	@api.model_create_multi
	def create(self, vals_list):
		context = self.env.context
		if context.get('sop_bank'):
			for vals in vals_list:
				vals.update({"is_sop_bank": True})
		return super().create(vals_list)
