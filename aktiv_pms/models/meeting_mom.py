# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MeetingMom(models.Model):
    _name = "meeting.mom"
    _description = "MOM"

    name = fields.Char(string="Name", compute="_compute_agenda")
    meeting_datetime = fields.Datetime(string="Meeting Date")
    extra_participants = fields.Char(string="Hidden Participants")
    feedback = fields.Char(string="Next Plan")
    notes = fields.Text(string="Notes")
    meeting_id = fields.Many2one("aktiv.meeting", string="Meeting")
    meeting_agenda_ids = fields.Many2many("meeting.agenda", string="Agenda")
    owner_ids = fields.Many2many("res.users")
    participants_ids = fields.Many2many("res.partner", string="Participants")

    @api.depends("meeting_agenda_ids")
    def _compute_agenda(self):
        self.name = " | ".join(self.meeting_agenda_ids.mapped("name")) or "New"
