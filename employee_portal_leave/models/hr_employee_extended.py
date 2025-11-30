from odoo import models, fields, api
from odoo.exceptions import AccessError
import logging

_logger = logging.getLogger(__name__)


class HrEmployeeExtended(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        """
        Restrict portal users to see only their own employee record
        """
        if self.env.user.has_group('base.group_portal'):
            # Use direct SQL query to avoid recursion
            self.env.cr.execute("""
                                SELECT id
                                FROM hr_employee
                                WHERE user_id = %s
                                  AND active = true LIMIT 1
                                """, (self.env.user.id,))

            result = self.env.cr.fetchone()

            if result:
                employee_id = result[0]
                domain = ['&', ('id', '=', employee_id)] + (domain or [])
            else:
                # No employee record found, return empty
                domain = [('id', '=', False)]

        return super(HrEmployeeExtended, self).search(domain, offset=offset, limit=limit, order=order)

    def read(self, fields=None, load='_classic_read'):
        """
        Restrict portal users to read only their own employee record
        """
        if self.env.user.has_group('base.group_portal'):
            # Check if user is trying to access their own record
            for employee in self:
                if employee.user_id.id != self.env.user.id:
                    raise AccessError("You can only access your own employee information.")

        return super(HrEmployeeExtended, self).read(fields=fields, load=load)

    def write(self, vals):
        """
        Prevent portal users from modifying employee records
        """
        if self.env.user.has_group('base.group_portal'):
            raise AccessError("Portal users cannot modify employee records.")

        return super(HrEmployeeExtended, self).write(vals)