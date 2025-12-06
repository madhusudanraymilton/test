from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError, UserError
import logging

_logger = logging.getLogger(__name__)


class PortalTeamLeader(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add leave request counts to portal home"""
        values = super()._prepare_home_portal_values(counters)
        if 'leave_count' in counters:
            try:
                domain = self._get_leave_domain()
                values['leave_count'] = request.env['hr.leave'].search_count(domain)
            except Exception as e:
                _logger.error("Error counting leaves: %s", str(e))
                values['leave_count'] = 0
        return values

    def _get_leave_domain(self):
        """Get domain for leave requests based on team leader access"""
        try:
            if not request.env.user.has_group('base.group_portal'):
                return []

            domain = []
            employee = request.env['hr.employee'].sudo().search([
                ('user_id', '=', request.env.user.id),
                ('is_team_leader', '=', True)
            ], limit=1)

            if employee:
                # Team leader: see team members' requests (excluding other team leaders)
                domain = [
                    ('employee_id.team_leader_id', '=', employee.id),
                    ('employee_id.is_team_leader', '=', False),
                    ('team_leader_approval', 'in', ['pending', 'approved', 'refused'])
                ]
            else:
                # Regular portal user: see only own requests
                domain = [('employee_id.user_id', '=', request.env.user.id)]

            return domain
        except Exception as e:
            _logger.error("Error in _get_leave_domain: %s", str(e))
            return []

    @http.route(['/my/leaves', '/my/leaves/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_leaves(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        """Portal page for leave requests"""
        try:
            values = self._prepare_portal_layout_values()
            HrLeave = request.env['hr.leave']

            domain = self._get_leave_domain()

            # Search count
            leave_count = HrLeave.search_count(domain) if domain else 0

            # Pager
            pager = portal_pager(
                url="/my/leaves",
                total=leave_count,
                page=page,
                step=self._items_per_page
            )

            # Search records
            if domain:
                leaves = HrLeave.search(
                    domain,
                    limit=self._items_per_page,
                    offset=pager['offset'],
                    order="create_date desc"
                )
            else:
                leaves = HrLeave

            values.update({
                'leaves': leaves,
                'page_name': 'leaves',
                'default_url': '/my/leaves',
                'pager': pager,
                'leave_count': leave_count,
            })
            return request.render("team_leader_approvals.portal_my_leaves", values)
        except Exception as e:
            _logger.error("Error in portal_my_leaves: %s", str(e))
            return request.redirect('/my')

    @http.route(['/my/leave/approve/<int:leave_id>'], type='http', auth="user", website=True, csrf=True)
    def portal_approve_leave(self, leave_id, **kw):
        """Approve leave request from portal"""
        try:
            leave_sudo = request.env['hr.leave'].sudo().browse(leave_id)

            # Check if leave exists
            if not leave_sudo.exists():
                return request.redirect('/my/leaves?error=not_found')

            # Check access
            if not self._check_team_leader_access(leave_sudo):
                return request.redirect('/my/leaves?error=access')

            if leave_sudo.team_leader_approval != 'pending':
                return request.redirect('/my/leaves?error=not_pending')

            # Approve the leave
            leave_sudo.action_team_leader_approve()

            return request.redirect('/my/leaves?message=approved')

        except (AccessError, MissingError) as e:
            _logger.error("Access error in portal_approve_leave: %s", str(e))
            return request.redirect('/my/leaves?error=access')
        except UserError as e:
            _logger.error("User error in portal_approve_leave: %s", str(e))
            return request.redirect('/my/leaves?error=user')
        except Exception as e:
            _logger.error("Error in portal_approve_leave: %s", str(e))
            return request.redirect('/my/leaves?error=unknown')

    @http.route(['/my/leave/refuse/<int:leave_id>'], type='http', auth="user", website=True, csrf=True)
    def portal_refuse_leave(self, leave_id, **kw):
        """Refuse leave request from portal"""
        try:
            leave_sudo = request.env['hr.leave'].sudo().browse(leave_id)

            # Check if leave exists
            if not leave_sudo.exists():
                return request.redirect('/my/leaves?error=not_found')

            # Check access
            if not self._check_team_leader_access(leave_sudo):
                return request.redirect('/my/leaves?error=access')

            if leave_sudo.team_leader_approval != 'pending':
                return request.redirect('/my/leaves?error=not_pending')

            # Refuse the leave
            leave_sudo.action_team_leader_refuse()

            return request.redirect('/my/leaves?message=refused')

        except (AccessError, MissingError) as e:
            _logger.error("Access error in portal_refuse_leave: %s", str(e))
            return request.redirect('/my/leaves?error=access')
        except UserError as e:
            _logger.error("User error in portal_refuse_leave: %s", str(e))
            return request.redirect('/my/leaves?error=user')
        except Exception as e:
            _logger.error("Error in portal_refuse_leave: %s", str(e))
            return request.redirect('/my/leaves?error=unknown')

    def _check_team_leader_access(self, leave):
        """Check if current user is the team leader for this leave"""
        try:
            if not request.env.user.has_group('base.group_portal'):
                return False

            employee = request.env['hr.employee'].sudo().search([
                ('user_id', '=', request.env.user.id),
                ('is_team_leader', '=', True)
            ], limit=1)

            if not employee:
                return False

            # Check if this leave belongs to a team member
            # AND ensure the team member is not another team leader
            return (
                    leave.employee_id.team_leader_id == employee and
                    not leave.employee_id.is_team_leader
            )
        except Exception as e:
            _logger.error("Error in _check_team_leader_access: %s", str(e))
            return False