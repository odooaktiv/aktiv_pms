from datetime import datetime

import pytz
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MeetingRescheduleDateWizard(models.TransientModel):
    _name = "meeting.reschedule.wizard"
    _description = "Meeting Mom Wizard"

    meeting_datetime = fields.Datetime(string="New Meeting Datetime")
    meeting_id = fields.Many2one("aktiv.meeting", string="Meeting")

    # reschedule datetime and state in reschedule stage
    def reschedule_datetime(self):
        if self.meeting_datetime < datetime.now():
            raise ValidationError(
                _("New meeting date should be greater than current date!")
            )
        (
            end_date,
            customer_tz,
            user_tz,
        ) = self.meeting_id.project_id.get_meeting_end_date()
        user_time = pytz.utc.localize(self.meeting_datetime).astimezone(user_tz)
        customer_time = pytz.utc.localize(self.meeting_datetime).astimezone(customer_tz)
        user_time_naive = user_time.replace(tzinfo=None)
        customer_time_naive = customer_time.replace(tzinfo=None)
        naive_diff = user_time_naive - customer_time_naive
        customer_date = self.meeting_datetime - naive_diff
        new_meeting = (
            self.env["aktiv.meeting"]
            .sudo()
            .create(
                {
                    "local_datetime": self.meeting_datetime,
                    "cust_datetime": customer_date,
                    "origin_meeting_ref": self.meeting_id.id,
                    "project_id": self.meeting_id.project_id.id,
                    "owner_ids": self.env.user,
                    "is_rescheduled": True,
                }
            )
        )
        self.meeting_id.state = "rescheduled"
        self.meeting_id.rescheduled_meeting_ref = new_meeting.id

    @api.onchange("meeting_datetime")
    def onchange_reschedule_date(self):
        """Method to check the rescheduling date in not same as Other meetings date"""
        if self.meeting_datetime:
            meeting_lines = self.env["aktiv.meeting"].search(
                [("project_id", "=", self.meeting_id.project_id.id)]
            )
            dates = []
            for rec in meeting_lines:
                dates.append(rec.local_datetime.date())
            if (
                self.meeting_datetime.date() in dates
            ) or self.meeting_datetime.date() <= self.meeting_id.project_id.generate_meeting_from.date():
                raise ValidationError(
                    _("New meeting date should not be same as other meeting dates!")
                )
