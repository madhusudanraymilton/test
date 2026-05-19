# from odoo import models


# class MailThread(models.AbstractModel):
#     _inherit = "mail.thread"

#     def message_post(self, **kwargs):

#         kwargs["message_type"] = "comment"

#         if not kwargs.get("subtype_xmlid"):
#             kwargs["subtype_xmlid"] = "mail.mt_comment"

#         return super().message_post(**kwargs)
from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_post(self, **kwargs):

        kwargs["message_type"] = "comment"

        kwargs["subtype_xmlid"] = "mail.mt_comment"

        return super().message_post(**kwargs)