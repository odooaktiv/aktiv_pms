from odoo import api, fields, models


class ProjectTags(models.Model):
	_inherit = "project.tags"

	is_sop_bank = fields.Boolean(string="SOP Bank")
	old_db_id = fields.Integer(string="Old DB ID", copy=False)

	def create(self, vals):
		context = self.env.context
		if context.get('sop_bank'):
			vals.update({"is_sop_bank": True})
		res = super().create(vals)
		return res
