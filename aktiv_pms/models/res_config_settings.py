# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ip_addr = fields.Char("PM Tool URL / IP", config_parameter="aktiv_pms.ip_addr", help="e.g. https://pms.aktivsoftware.com or 192.46.214.132:8015")
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
