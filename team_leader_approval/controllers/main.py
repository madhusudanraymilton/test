from odoo import http
from odoo.http import request


class TeamLeaderApprovalController(http.Controller):

    # Main page to display all leave approvals
    @http.route('/my/leave/team-leader/approvals', type='http', auth='user', website=True)
    def team_leader_approvals_page(self, **kw):
        """Display the team leader approval page with all necessary data"""

        # Get current user's employee record
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id)
        ], limit=1)

        return request.render('team_leader_approval.portal_team_leader_approvals', {
            'user': user,
        })