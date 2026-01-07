# -*- coding: utf-8 -*-

import pytz
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AktivMeetings(models.Model):
    _name = "aktiv.meeting"
    _description = "Meetings"

    name = fields.Char(string="Name", compute="_compute_meeting_name", store=True)
    local_datetime = fields.Datetime(_("Local DateTime"))
    cust_datetime = fields.Datetime(_("Customer DateTime"))
    owner_ids = fields.Many2many("res.users")
    participants_ids = fields.Many2many("res.partner", string="Participants")
    project_id = fields.Many2one("project.project", "Project")
    state = fields.Selection(
        [
            ("scheduled", "Scheduled"),
            ("rescheduled", "Rescheduled"),
            ("missed", "Missed"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        string="Stage",
        default="scheduled",
    )
    meeting_cancellation_reason = fields.Text(string="Meeting Cancellation Reason")
    mom_id = fields.Many2one("meeting.mom", string="MOM")
    rescheduled_meeting_ref = fields.Many2one(
        "aktiv.meeting", string="Rescheduled Meeting Reference"
    )
    origin_meeting_ref = fields.Many2one(
        "aktiv.meeting", string="Origin Meeting Reference"
    )
    is_rescheduled = fields.Boolean(string="Is Rescheduled")
    meeting_video_url = fields.Char(string="Meeting Video Url")

    @api.onchange("local_datetime", "cust_datetime")
    def onchange_local_cust_datetime(self):
        if self.local_datetime:
            end_date, customer_tz, user_tz = self.project_id.get_meeting_end_date()
            user_time = pytz.utc.localize(self.local_datetime).astimezone(user_tz)
            # local datetime convert in customer TZ
            customer_time = pytz.utc.localize(self.local_datetime).astimezone(
                customer_tz
            )
            # get naive time to get actual timedelta as with aware dates the
            # delta is based on UTC
            user_time_naive = user_time.replace(tzinfo=None)
            customer_time_naive = customer_time.replace(tzinfo=None)
            # timedelta between user and cust timezone
            naive_diff = user_time_naive - customer_time_naive
            self.cust_datetime = self.local_datetime - naive_diff

    def unlink(self):
        if not self.env.context.get("for_generate", False):
            for rec in self:
                message = _(
                    "Deleted meeting:<br/>"
                    "Name: %s<br/>"
                    "Local DateTime: %s<br/>"
                    "Owner: %s"
                ) % (
                    rec.name,
                    rec.local_datetime,
                    (", ".join(rec.owner_ids.mapped("name"))),
                )
                self.project_id.message_post(body=message)
        return super(AktivMeetings, self).unlink()

    def mom_view(self):
        """
        return mom tree and form view
        """
        return {
            "type": "ir.actions.act_window",
            "name": "MOM",
            "view_mode": "form",
            "res_model": "meeting.mom",
            "res_id": self.mom_id.id,
            "target": "current",
        }

    def add_mom(self):
        """
        return mom wizard
        """
        return self.action_complete()

    def update_mom(self):
        """
        return update mom wizard
        """
        if self.id == self.mom_id.meeting_id.id:
            return {
                "name": "Meeting MOM",
                "type": "ir.actions.act_window",
                "res_model": "meeting.mom.wizard",
                "view_mode": "form",
                "view_type": "form",
                "context": {
                    "default_meeting_id": self.mom_id.meeting_id.id,
                    "default_meeting_datetime": self.mom_id.meeting_datetime,
                    "default_meeting_agenda_ids": [
                        (6, 0, self.mom_id.meeting_agenda_ids.ids)
                    ],
                    "default_name": self.mom_id.name,
                    "default_extra_participants": self.mom_id.extra_participants,
                    "default_feedback": self.mom_id.feedback,
                    "default_notes": self.mom_id.notes,
                    "default_mom_id": self.mom_id.id,
                    "default_participants_ids": [
                        (6, 0, self.mom_id.participants_ids.ids)
                    ],
                    "default_owner_ids": [(6, 0, self.mom_id.owner_ids.ids)],
                },
                "target": "new",
            }

    @api.depends("project_id", "local_datetime")
    def _compute_meeting_name(self):
        """
        compute meeting name
        """
        for rec in self:
            name = ""
            if rec.is_rescheduled:
                name += "Reschedule: "
            if rec.project_id and rec.project_id.name:
                name += rec.project_id.name + " - "
            if rec.local_datetime:
                name += str(rec.local_datetime)
            rec.name = name

    def action_complete(self):
        """
        return mom wizard and default pass meeting id
        """
        pending_meetings = self.search(
            [
                ("project_id", "=", self.project_id.id),
                ("local_datetime", "<", self.local_datetime),
                ("state", "=", "scheduled"),
            ]
        )
        if pending_meetings:
            raise ValidationError(_("Please complete older meetings first!"))
        return {
            "name": "Meeting MOM",
            "type": "ir.actions.act_window",
            "res_model": "meeting.mom.wizard",
            "view_mode": "form",
            "view_type": "form",
            "context": {
                "default_meeting_id": self.id,
                "default_meeting_datetime": self.local_datetime,
                "default_owner_ids": [(6, 0, self.owner_ids.ids)],
                "default_participants_ids": [(6, 0, self.participants_ids.ids)],
            },
            "target": "new",
        }

    def action_reschedule(self):
        """
        return meeting reschedule wizard with default meeting id
        """
        return {
            "name": "Meeting Reschedule Date",
            "type": "ir.actions.act_window",
            "res_model": "meeting.reschedule.wizard",
            "view_mode": "form",
            "view_type": "form",
            "context": {"default_meeting_id": self.id},
            "target": "new",
        }

    def action_cancel(self):
        """
        return meeting cancellation wizard with default meeting id
        """
        return {
            "name": "Meeting Cancellation Reason",
            "type": "ir.actions.act_window",
            "res_model": "meeting.cancellation.wizard",
            "view_mode": "form",
            "view_type": "form",
            "context": {"default_meeting_id": self.id},
            "target": "new",
        }

    def action_reset(self):
        """
        reset meeting with remove mom, cancellation reason

        """
        if (
            self.rescheduled_meeting_ref
            or self.cust_datetime
            or self.meeting_cancellation_reason
        ):
            self.meeting_cancellation_reason = False
            self.rescheduled_meeting_ref.mom_id.unlink()
            self.rescheduled_meeting_ref.unlink()
            self.mom_id.unlink()
            self.write({"state": "scheduled"})
