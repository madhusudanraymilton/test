from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from odoo.addons.portal.controllers.portal import CustomerPortal
import logging

_logger = logging.getLogger(__name__)

class PortalLoginRedirectController(http.Controller):

    @http.route('/my-portal', type='http', auth='user', website=True)
    def portal_dashboard(self, **kw):
        print("##################################Portal Login Redirect is Activated ###############################")
        user = request.env.user
        return request.render('portal_login_redirect.portal_dashboard', {
            'user': user,
        })

class PortalRedirect(Home):

    def _login_redirect(self, uid, redirect=None):
        """Redirect portal users to /my and employees to backend."""
        user = request.env['res.users'].sudo().browse(uid)

        # Internal backend users → go to web backend
        if user.has_group("base.group_user"):
            return super()._login_redirect(uid, redirect)

        # Portal users → go to portal dashboard (/my)
        if user.has_group("base.group_portal"):
            print("This section is Activated....................................portal redirect class")
            return "/my-portal"

        # Default behavior for other cases
        return super()._login_redirect(uid, redirect)


class MasterPortalRedirect(CustomerPortal):
    @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        """Override portal home - this should take precedence"""
        _logger.info(f"MASTER REDIRECT: Portal home override for user {request.env.user.id}")
        print("############################################MASTER REDIRECT#######################################################################")
        return request.redirect('/my-portal')


