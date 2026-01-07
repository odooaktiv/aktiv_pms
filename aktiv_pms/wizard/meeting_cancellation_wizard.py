from odoo import fields, models


class MeetingCancellationWizard(models.TransientModel):
    _name = "meeting.cancellation.wizard"
    _description = "meeting cancellation reason wizard"

    meeting_cancel_reason = fields.Text(string="Meeting Cancellation Reason")
    meeting_id = fields.Many2one("aktiv.meeting", string="Meeting")

    # write cancellation reason in meeting and state in cancel stage
    def meeting_cancellation_reason(self):
        if self.meeting_cancel_reason and self.meeting_id:
            self.meeting_id.write(
                {"meeting_cancellation_reason": self.meeting_cancel_reason}
            )
            self.meeting_id.state = "cancelled"
