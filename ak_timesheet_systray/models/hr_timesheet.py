from odoo import _, api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.model_create_multi
    def create(self, vals_list):
        res = super(AccountAnalyticLine, self).create(vals_list)
        for record in res:
            self.env['bus.bus']._sendone(f'unsync_timesheet_update_{record.user_id.id}',  # Channel
                                         'unsync_timesheet_update',  # Notification type
                                         {'user_id': record.user_id.id,  # Relevant user ID
                                          'action': 'update_counter',  # Action to trigger in JS
                                          })
        return res

    def write(self, vals):
        """Method Override to update state when timesheet entries are updated"""
        # Log approved hours history

        result = super(AccountAnalyticLine, self).write(vals)

        if vals.get('data_sync') :
            for rec in self:
                # Send a bus notification to trigger the counter update in JS
                self.env['bus.bus']._sendone(f'unsync_timesheet_update_{rec.user_id.id}',  # Channel
                    'unsync_timesheet_update',  # Notification type
                    {'user_id': rec.user_id.id,  # Relevant user ID
                        'action': 'update_counter',  # Action to trigger in JS
                    })
        return result