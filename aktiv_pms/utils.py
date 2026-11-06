import logging
from urllib.parse import urlparse

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
            # Accept "host:port", "host", "http://host[:port]" or "https://host[:port]"
            value = ip_addr.strip()
            if "://" not in value:
                value = "http://" + value
            parsed = urlparse(value)
            hostname = parsed.hostname
            secure = parsed.scheme == "https"
            port = parsed.port or (443 if secure else 80)
            protocol = "jsonrpc+ssl" if secure else "jsonrpc"

            # Establish the connection
            odoo_rpc = odoorpc.ODOO(hostname, protocol=protocol, port=port)
            odoo_rpc.login(db_name, username, password)
            return odoo_rpc
        except Exception as e:
            raise ValidationError(f"Connection to the Odoo instance failed: {e}")
    else:
        raise ValidationError("Missing connection parameters for the Odoo instance.")
