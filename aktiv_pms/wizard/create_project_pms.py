import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..utils import get_connection

_logger = logging.getLogger(__name__)


class ProjectCreationWizard(models.TransientModel):
    _name = 'project.creation.wizard'
    _description = 'Create Project Wizard'

    name = fields.Char('Name')
    partner_id = fields.Many2one('res.partner', string='Partner')
    task = fields.Char('Task name', required=True)

    def create_pms_project(self):
        """Method which will connect the db of pm tool and create the project and general task
        in aktiv pmtool"""

        context = self.env.context
        project = self.env['project.project']
        if context.get('active_model') == 'project.project':
            b2c_project_id = project.browse(context.get('active_id'))
        else:
            b2c_project_id = project.search([('name','=',self.name)])
        b2c_project_id.is_project_create = True
        try:
            odoo_conn = get_connection(self.env)
        except Exception as e:
            raise ValidationError(e)
        if not odoo_conn:
            raise ValidationError("Please establish connection with database!")
        odoo_conn.env.context.update({'mail_create_nosubscribe': True, 'mail_create_nolog': True})
        partner = odoo_conn.env["res.partner"].search([('name', 'ilike', self.partner_id.name)], limit=1)
        if partner:
            partner_id = partner[0]
        else:
            partner_id = odoo_conn.env["res.partner"].create({'name': self.partner_id.name})

        if not partner_id:
            raise ValidationError("Partner creation failed!")


        # Project PO
        b2c_project_user = b2c_project_id.user_id.user_name
        b2b_po_id = odoo_conn.env['res.users'].search([('login', '=', b2c_project_user)], limit=1)
        b2b_po_user_id = b2b_po_id[0] if b2b_po_id else False

        #Project Team Member
        team_member_ids = [odoo_conn.env.uid]
        users = b2c_project_id.get_b2b_users(odoo_conn)
        team_member_ids.extend(users)

        b2c_user = odoo_conn.env['res.users'].read(odoo_conn.env.uid, ['employee_id'])
        b2c_employee_id = b2c_user[0].get('employee_id')[0] if b2c_user else False
        b2c_parent_id = odoo_conn.env['hr.employee'].browse(b2c_employee_id).parent_id if b2c_employee_id else False
        b2c_parent_user_data = odoo_conn.env['hr.employee'].read(b2c_parent_id.id, ['user_id']) if b2c_parent_id else False
        b2c_parent_user_id = b2c_parent_user_data[0].get('user_id')[0] if b2c_parent_user_data else False

        b2c_project_category_id = odoo_conn.env.ref('pms_tool.customer_projects').id

        project_values = {'name': self.name,
                          'partner_id': partner_id,
                          'coach_id': b2c_employee_id,
                          'user_id': b2c_parent_user_id,
                          'department_ids': [(6, 0, b2c_parent_id.department_id.ids)],
                          'team_member_ids': [(6, 0, team_member_ids)],
                          'project_category_id': b2c_project_category_id, 
                          'project_owner_id': b2b_po_user_id,
                          }
        try:
            project_val = odoo_conn.env['project.project'].create(project_values)
        except Exception as e:
            _logger.error("Error creating project: %s", e)
            raise ValidationError("Error creating project: %s" % str(e))

        task_id = odoo_conn.env['project.task'].create({
            'name': self.task,
            'project_id': project_val,
            'B2C_task_sync': True
            })

        b2b_project_task = odoo_conn.env['project.task'].read(task_id, ['name', 'project_id'])
        if b2b_project_task and b2c_project_id:
            b2c_project_id.sudo().write({'pm_tool_project_id': b2b_project_task[0].get('project_id')[0],
                                         'pm_tool_task_id': b2b_project_task[0].get('id'),
                                         'pm_tool_task_name': b2b_project_task[0].get('name'),
                                        })
        return b2c_project_id
