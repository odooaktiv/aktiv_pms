from odoo import api, fields, models


class MeetingMomWizard(models.TransientModel):
    _name = "meeting.mom.wizard"
    _description = "Meeting Mom Wizard"

    name = fields.Char(string="Name", compute="_compute_agenda")
    meeting_datetime = fields.Datetime(string="Meeting Date")
    extra_participants = fields.Char(string="Hidden Participants")
    feedback = fields.Char(string="Next Plan")
    notes = fields.Text(string="Notes")
    meeting_id = fields.Many2one("aktiv.meeting", string="Meeting")
    meeting_agenda_ids = fields.Many2many("meeting.agenda", string="Agenda")
    participants_ids = fields.Many2many("res.partner", string="Participants")
    owner_ids = fields.Many2many("res.users", string="Owner")
    mom_id = fields.Many2one("meeting.mom", string="MOM")

    @api.depends("meeting_agenda_ids")
    def _compute_agenda(self):
        self.name = " | ".join(self.meeting_agenda_ids.mapped("name")) or "New"

    # create mom and state in complete stage
    def create_mom(self):
        vals = {
            "name": self.name,
            "meeting_datetime": str(self.meeting_datetime),
            "meeting_id": self.meeting_id.id,
            "extra_participants": self.extra_participants,
            "feedback": self.feedback,
            "notes": self.notes,
            "meeting_agenda_ids": self.meeting_agenda_ids,
            "participants_ids": self.participants_ids,
            "owner_ids": self.owner_ids,
        }
        if self.mom_id:
            self.mom_id.write(vals)
        else:
            mom = self.env["meeting.mom"].create(vals)
            mom.meeting_id.state = "completed"
            mom.meeting_id.mom_id = mom.id
