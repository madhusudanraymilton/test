from odoo import models, fields, api
from odoo.exceptions import AccessError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class HrLeaveExtended(models.Model):
    _inherit = 'hr.leave'

    delegate_employee_id = fields.Many2one(
        'hr.employee',
        string='Delegate To',
        help='Employee who will handle responsibilities during leave',
        tracking=True
    )

    @api.constrains('employee_id', 'delegate_employee_id')
    def _check_delegate_employee(self):
        for leave in self:
            if leave.delegate_employee_id and leave.employee_id == leave.delegate_employee_id:
                raise ValidationError('You cannot delegate to yourself!')

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        """Restrict portal users to see ONLY their own leaves"""
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
                domain = ['&', ('employee_id', '=', employee_id)] + (domain or [])
            else:
                # No employee record, return empty
                domain = [('id', '=', False)]

        return super(HrLeaveExtended, self).search(domain, offset=offset, limit=limit, order=order)

    def read(self, fields=None, load='_classic_read'):
        """Prevent portal users from reading others' leave records"""
        if self.env.user.has_group('base.group_portal'):
            # Use direct SQL to get employee
            self.env.cr.execute("""
                                SELECT id
                                FROM hr_employee
                                WHERE user_id = %s
                                  AND active = true LIMIT 1
                                """, (self.env.user.id,))

            result = self.env.cr.fetchone()
            employee_id = result[0] if result else None

            for leave in self:
                if not employee_id or leave.employee_id.id != employee_id:
                    raise AccessError("You can only view your own leave requests.")

        return super(HrLeaveExtended, self).read(fields=fields, load=load)

    def write(self, vals):
        """Restrict portal users from modifying approved/refused leaves"""
        if self.env.user.has_group('base.group_portal'):
            # Use direct SQL to get employee
            self.env.cr.execute("""
                                SELECT id
                                FROM hr_employee
                                WHERE user_id = %s
                                  AND active = true LIMIT 1
                                """, (self.env.user.id,))

            result = self.env.cr.fetchone()
            employee_id = result[0] if result else None

            for leave in self:
                if leave.state not in ['draft', 'confirm']:
                    raise AccessError("You cannot modify approved or refused leave requests.")

                if not employee_id or leave.employee_id.id != employee_id:
                    raise AccessError("You can only modify your own leave requests.")

        return super(HrLeaveExtended, self).write(vals)

    def unlink(self):
        """Prevent portal users from deleting leaves"""
        if self.env.user.has_group('base.group_portal'):
            raise AccessError("Portal users cannot delete leave requests. Please cancel instead.")

        return super(HrLeaveExtended, self).unlink()


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        """Restrict portal users to see ONLY their own allocations"""
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
                domain = ['&', ('employee_id', '=', employee_id)] + (domain or [])
            else:
                domain = [('id', '=', False)]

        return super(HrLeaveAllocation, self).search(domain, offset=offset, limit=limit, order=order)

    def read(self, fields=None, load='_classic_read'):
        """Prevent portal users from reading others' allocations"""
        if self.env.user.has_group('base.group_portal'):
            # Use direct SQL to get employee
            self.env.cr.execute("""
                                SELECT id
                                FROM hr_employee
                                WHERE user_id = %s
                                  AND active = true LIMIT 1
                                """, (self.env.user.id,))

            result = self.env.cr.fetchone()
            employee_id = result[0] if result else None

            for allocation in self:
                if not employee_id or allocation.employee_id.id != employee_id:
                    raise AccessError("You can only view your own leave allocations.")

        return super(HrLeaveAllocation, self).read(fields=fields, load=load)

    def write(self, vals):
        """Prevent portal users from modifying allocations"""
        if self.env.user.has_group('base.group_portal'):
            raise AccessError("Portal users cannot modify leave allocations.")

        return super(HrLeaveAllocation, self).write(vals)

    def unlink(self):
        """Prevent portal users from deleting allocations"""
        if self.env.user.has_group('base.group_portal'):
            raise AccessError("Portal users cannot delete leave allocations.")

        return super(HrLeaveAllocation, self).unlink()