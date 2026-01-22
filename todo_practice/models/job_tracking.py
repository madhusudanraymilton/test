from odoo import models, fields, api

class JobTracking(models.Model):
    _name = "job.tracking"
    _description = "Job Tracking"
    _inherit = ['mail.thread']
    #_rec_name = name

    name = fields.Char(string="Applicant Name ", tracking=True)
    job_id = fields.Char(string="Job Position", tracking=True)
    stages = fields.Selection(
        [('new', "New"), ('interview', "Interview"), ("offer", "Offer"), ("hired", "Hired")],
        default="new", tracking=True
    )
