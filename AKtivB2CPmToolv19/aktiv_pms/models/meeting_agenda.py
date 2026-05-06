# -*- coding: utf-8 -*-

from odoo import fields, models


class MeetingAgenda(models.Model):
    _name = "meeting.agenda"
    _description = "Meeting Agenda"
    name = fields.Char(string="Name")
