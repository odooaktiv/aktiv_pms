# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ip_addr = fields.Char("IP Address", config_parameter="aktiv_pms.ip_addr")
    db_name = fields.Char("Database", config_parameter="aktiv_pms.db_name")
    master_uid = fields.Char("Master Username", config_parameter="aktiv_pms.master_uid")
    master_pwd = fields.Char("Master Password", config_parameter="aktiv_pms.master_pwd")
    timesheet_locking_period = fields.Char(
        string='Timesheet Locking Period (days)',
        config_parameter='aktiv_pms.timesheet_locking_period',
    )
    revoke_group_access = fields.Char(
        string='Revoke Group Access (days)',
        config_parameter='aktiv_pms.revoke_group_access',
    )
