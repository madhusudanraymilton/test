from odoo import http
from odoo.http import request

class TeamLeaderApprovalController(http.Controller):
    @http.route('/team_leader/approve', type='http', auth='user', website=True)
    def approve_request(self, request_id):
       for rec in self:
           return request.render('team_leader_approval.portal_team_leader_approvals', {
               'request_id': request_id,
           })