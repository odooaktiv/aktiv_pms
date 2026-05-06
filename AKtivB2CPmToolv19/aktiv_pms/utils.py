import logging

import odoorpc
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def get_connection(env):
    """Generic method to connect to the PM tool to fetch and create data."""
    ip_addr = env["ir.config_parameter"].sudo().get_param("aktiv_pms.ip_addr")
    db_name = env["ir.config_parameter"].sudo().get_param("aktiv_pms.db_name")
    username = env["ir.config_parameter"].sudo().get_param("aktiv_pms.master_uid")
    password = env["ir.config_parameter"].sudo().get_param("aktiv_pms.master_pwd")

    if ip_addr and db_name and username and password:
        try:
            # Extract hostname and port from the IP address
            hostname, port = ip_addr.split(":")
            port = int(port)
            
            # Establish the connection
            odoo_rpc = odoorpc.ODOO(hostname, port=port)
            odoo_rpc.login(db_name, username, password)
            return odoo_rpc
        except Exception as e:
            raise ValidationError(f"Connection to the Odoo instance failed: {e}")
    else:
        raise ValidationError("Missing connection parameters for the Odoo instance.")
