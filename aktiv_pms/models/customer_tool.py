# -*- coding: utf-8 -*-

from odoo import fields, models


class ProjectCustomerTool(models.Model):
    """A tool the customer already uses or used before (Jira, Trello, Excel sheets, ...).

    Only a name: it is picked as tags on the project form of customer projects."""

    _name = "project.customer.tool"
    _description = "Customer Tool"
    _order = "name"

    name = fields.Char(required=True)

    _name_uniq = models.Constraint("UNIQUE(name)", "This tool already exists.")
