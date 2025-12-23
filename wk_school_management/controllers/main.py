# -*- coding: utf-8 -*-
#################################################################################
#
# Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>; )
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>;
#
#################################################################################
import base64

import logging
from odoo import http
from odoo.http import request, Controller
from datetime import datetime, date, timedelta
from odoo import fields, _
from odoo.addons.mail.controllers.mail import MailController

_logger = logging.getLogger(__name__)


class WebsiteMenuApplication(http.Controller):

    @http.route('/OnlineRegistration', type='http', website=True, auth="public")
    def application_form(self, **kw):
        website = request.env['website'].get_current_website()
        school = website.company_id
        states = request.env['res.country.state'].sudo().search_read([], [
            'name', 'country_id'])
        country = request.env['res.country'].sudo().search_read([], ['name'])
        domain = [('company_id', '=', int(school))]
        filtered_classes = request.env['wk.school.grade'].sudo().search_read(domain, ['name'])
        blood_groups = dict(request.env['wk.application.form']._fields['blood_group'].selection)
        document_ids = school.required_document_ids
        child_ids = school.sudo().child_ids
        values = {
            'school': school,
            'classes': filtered_classes,
            'states': states,
            'country': country,
            'blood_groups': blood_groups,
            'document_ids': document_ids,
            'branches': child_ids
        }
        return request.render("wk_school_management.application_form_template", values)

    @http.route(['/application/submit/'], type='http', methods=['POST'], website='True', auth="public", csrf=True)
    def application_submit(self, **kw):
        first_name = kw.pop('first_name')
        last_name = kw.pop('last_name')
        mother_name = kw.pop('mother_name')
        father_name = kw.pop('father_name')
        state_id = kw.pop('state_id')
        country_id = kw.pop('country_id')
        company_id = kw.pop('company_id')
        queries = kw.pop('queries')
        student_image = kw.pop('student_image')
        grade_id = kw.pop('grade_id')

        vals = {
            'student_name': first_name + " " + last_name,
            'mother_name': mother_name,
            'father_name': father_name,
            'queries': queries,
            'state_id': int(state_id) if state_id != '0' else False,
            'country_id': int(country_id) if country_id != '0' else False,
            'company_id': int(company_id),
            'grade_id': int(grade_id),
            'name': request.env['ir.sequence'].sudo().next_by_code(
                'application.form.sequence') or _("New"),
            'student_image': base64.b64encode(student_image.read()).decode('utf-8')
        }
        vals.update(kw)
        # vals.pop('g-recaptcha-response')
        if vals.get('child_id'):
            vals.pop('child_id')
        company = request.env['res.company'].sudo().browse(int(company_id))
        documents = company.required_document_ids
        variable_attachments = {}
        for document in documents:
            if document.name in vals:
                variable_attachments[f'{document.name}'] = vals.get(f'{document.name}')
                vals.pop(f'{document.name}')

        application = request.env['wk.application.form'].sudo().create(vals)
        attachment_vals = []
        for key, value in variable_attachments.items():
            filename = key
            file_data = value.read()
            report_base64 = base64.b64encode(file_data)
            attachment_vals.append({
                'name': filename,
                'res_model': 'wk.application.form',
                'res_id': application.id,
                'type': 'binary',
                'datas': report_base64,
            })

        if attachment_vals:
            attachment_ids = request.env['ir.attachment'].sudo().create(attachment_vals)
            application.write({
                'attachment_ids': [(6, 0, attachment_ids.ids)]
            })
        application_number = vals['name']

        return request.redirect(f'/application/success?application_number={application_number}')

    @http.route('/application/success/', type='http', website=True, auth="public")
    def application_form_success(self, **kw):
        app_number = kw.get('application_number')
        values = {
            'application_number': app_number
        }
        return request.render("wk_school_management.application_submit_template", values)

    @http.route(['/application_search'], type='http', auth="public", website=True)
    def application_search(self, **kw):
        return request.render("wk_school_management.portal_application_search", {})

    @http.route(['/application/status'], type='http', auth="public", website=True)
    def application_status(self, **kw):
        if not kw.get('application_number'):
            return request.redirect('/application_search')

        application_number = kw.get('application_number')
        application_id = request.env['wk.application.form'].sudo().search([('name', '=', application_number)])

        if not application_id:
            return request.render("wk_school_management.no_application_found", {'application_number':application_number})

        return request.render("wk_school_management.portal_application_status", {'application_id':application_id})

    @http.route('/company/branch/grades',type='json',website=True, auth="public")
    def get_company_grades(self, **kw):
        companyId = kw.pop('branch_id')
        branch_id = request.env['res.company'].sudo().browse(int(companyId))
        domain = [('company_id', '=', branch_id.id)]
        filtered_classes = request.env['wk.school.grade'].sudo().search_read(domain, ['name'])
        document_ids = branch_id.sudo().required_document_ids
        documents = [{'id': doc.id, 'name': doc.name} for doc in document_ids] 
        values = {
            'classes': filtered_classes,
            'document_ids': documents,
            'google_map_link': branch_id.partner_id.google_map_link()
        }
        return values

    @http.route('/company/details', type='json', website=True, auth="public")
    def get_company_details(self, **kw):
        user = request.env.user
        branchId = kw.get('branchId')
        if branchId:
            company_id = int(branchId)
        else:
            company_id = user.company_id.id
        company = request.env['res.company'].sudo().browse(company_id)
        address = (
            f"{company.street if company.street else ''}, "
            f"{company.street2 if company.street2 else ''}, "
            f"{company.city if company.city else ''}, "
            f"{company.zip if company.zip else ''}, "
            f"{company.state_id.name if company.state_id.name else ''}, "
            f"{company.country_id.name if company.country_id.name else ''}"
        )
        name = company.name
        phone = company.phone if company.phone else ""
        return address, name, phone

    @http.route('/filter/state', type='json', website=True, auth="public")
    def filter_states(self, country, **kw):
        domain = []
        if country and country != 'country':
            domain += [('country_id', '=', int(country))]
        filtered_states = request.env['res.country.state'].sudo().search_read(domain, [
            'name', 'country_id'])
        return {'states': filtered_states}

    @http.route('/school_management/profile_data', type='json', website=True, auth="user")
    def school_profile_data(self, **kw):
        values = {}
        user = request.env.user

        employee_id = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)])

        subjects = {'subjects': employee_id.subject_ids[:5]}

        values['employee_id'] = employee_id.id
        values['name'] = employee_id.name
        values['profile'] = f'/web/image/hr.employee/{employee_id.id}/avatar_128'
        values['job_title'] = employee_id.job_title if employee_id.job_title else ""
        values['email'] = employee_id.work_email if employee_id.work_email else ""
        values['phone'] = employee_id.work_phone if employee_id.work_phone else ""
        body = request.env['ir.qweb']._render('wk_school_management.teacher_subjects', subjects)
        values['subjects'] = body
        return values

    @http.route('/school_management/dashboard_data', type='json', website=True, auth="user")
    def school_dashboard_data(self, **kw):
        values = {}
        today = datetime.today().date()
        company_id = [int(company) for company in kw.get('company_id').split('-')]

        application_count = request.env['wk.application.form'].sudo().search_count([('company_id', 'in', company_id)])
        enrollment_count = request.env['student.enrollment'].sudo().search_count([('company_id', 'in', company_id)])
        student_count = request.env['student.student'].search_count([('company_id', 'in', company_id)])
        faculty_count = request.env['hr.employee'].sudo().search_count([('company_id', 'in', company_id), ('is_teacher', '=', True)])

        values['total_application_count'] = application_count
        values['total_enrollment_count'] = enrollment_count
        values['total_student_count'] = student_count
        values['total_faculty_count'] = faculty_count

        present_students = request.env['wk.student.attendance'].search_count([
            ('attendance_state', '=', 'present'),
            ('attendance_date', '=', today),
            ('company_id', 'in', company_id)
        ])
        absent_students = student_count - present_students

        present_faculty = 0
        absent_faculty = 0

        present_faculty = request.env['hr.employee'].search_count([
            ('is_teacher', '=', True),
            ('last_check_in', '>=', today.strftime('%Y-%m-%d 00:00:00')),
            ('company_id', 'in', company_id)
        ])
        absent_faculty = faculty_count - present_faculty

        user = request.env.user
        is_admin = user.has_group('wk_school_management.wk_school_management_officer_group')

        if not is_admin:
            classes_count = request.env['wk.class.timetable'].search_count([('company_id','in', company_id)])
            assigned_assignments = request.env['wk.class.assignment'].search_count([('company_id', 'in', company_id)])
            student_assignments = request.env['wk.student.assignment'].search_count([('company_id', 'in', company_id)])
            service_hours = request.env['wk.service.hours'].search_count([('company_id', 'in', company_id), ('state', '=', 'new')])

            values['total_classes_count'] = classes_count
            values['total_assigned_assignments'] = assigned_assignments
            values['total_student_assignments'] = student_assignments
            values['total_service_hours'] = service_hours

        values['is_admin'] = is_admin
        values['teachers'] = [present_faculty, absent_faculty]
        values['students'] = [present_students, absent_students]
        return values

    @http.route('/school_management/datewise_data', type='json', website=True, auth="user")
    def load_datewise_data(self,**kw):
        values = {}
        user = request.env.user
        selected_date = kw.get('sort_date')
        current_date = datetime.today()
        company_id = [int(company) for company in kw.get('company_id').split('-')]

        if selected_date == 'week':
            start_date = current_date - timedelta(days=current_date.weekday())
            end_date = start_date + timedelta(days=6)

        elif selected_date == 'month':
            start_date = current_date.replace(day=1)
            next_month = current_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)

        elif selected_date == 'year':
            start_date = current_date.replace(month=1, day=1)
            end_date = current_date.replace(month=12, day=31)

        notice_ids = request.env['wk.notice.board'].search([
            ('state', '=', 'active'),
            ('start_date', '<=', end_date),
            ('end_date', '>=', start_date),
            ('company_id', 'in', company_id)
        ], order='create_date desc')

        lesson_plan_ids = request.env['wk.lesson.plan'].search(
            [('company_id', 'in', company_id), ('subject_id.id', 'in', user.employee_id.subject_ids.ids), ('plan_visibility', '=', 'all')], order='create_date desc')
        notice_data = {}
        lesson_data = {}
        if notice_ids:
            notice_data['notice_ids'] = notice_ids
        if lesson_plan_ids:
            lesson_data['lesson_plan_ids'] = lesson_plan_ids

        lesson_body = request.env['ir.qweb']._render('wk_school_management.lesson_plan', lesson_data)
        body = request.env['ir.qweb']._render('wk_school_management.notice_board', notice_data)
        values['notice_data'] = body
        values['lesson_data'] = lesson_body
        return values

    @http.route('/school_management/class_assignment', type='json', website=True, auth="user")
    def class_assignment_data(self, **kw):
        values = {}
        state = kw.get('sort_by')
        selected_date = kw.get('sort_date')
        current_date = datetime.today()
        company_id = [int(company) for company in kw.get('company_id').split('-')]

        if selected_date == 'week':
            start_date = current_date - timedelta(days=current_date.weekday())
            end_date = start_date + timedelta(days=6)

        elif selected_date == 'month':
            start_date = current_date.replace(day=1)
            next_month = current_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)

        elif selected_date == 'year':
            start_date = current_date.replace(month=1, day=1)
            end_date = current_date.replace(month=12, day=31)

        if state != 'all':
            assignments = request.env['wk.class.assignment'].search([
                ('state', '=', state),
                ('start_date', '>=', start_date),
                ('end_date', '<=', end_date),
                ('company_id', 'in', company_id)
            ], order='create_date desc')
        else:
            assignments = request.env['wk.class.assignment'].search([
                ('start_date', '>=', start_date),
                ('end_date', '<=', end_date),
                ('company_id', 'in', company_id)
            ], order='create_date desc')

        values['assignment_ids'] = assignments
        body = request.env['ir.qweb']._render('wk_school_management.class_assignment', values)
        return body

    @http.route('/school_management/student_assignment', type='json', website=True, auth="user")
    def student_assignment_data(self, **kw):
        values = {}
        state = kw.get('sort_by')
        selected_date = kw.get('sort_date')
        current_date = datetime.today()
        company_id = [int(company) for company in kw.get('company_id').split('-')]

        if selected_date == 'week':
            start_date = current_date - timedelta(days=current_date.weekday())
            end_date = start_date + timedelta(days=6)

        elif selected_date == 'month':
            start_date = current_date.replace(day=1)
            next_month = current_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)

        elif selected_date == 'year':
            start_date = current_date.replace(month=1, day=1)
            end_date = current_date.replace(month=12, day=31)

        if state != 'all':
            assignments = request.env['wk.student.assignment'].search([
                ('state', '=', state),
                ('start_date', '>=', start_date),
                ('end_date', '<=', end_date),
                ('company_id', 'in', company_id)
            ], order='create_date desc')
        else:
            assignments = request.env['wk.student.assignment'].search([
                ('start_date', '>=', start_date),
                ('end_date', '<=', end_date),
                ('company_id', 'in', company_id)
            ], order='create_date desc')

        values['assignment_ids'] = assignments
        body = request.env['ir.qweb']._render('wk_school_management.student_assignment', values)
        return body

    @http.route('/school_management/scheduled_classes', type='json', website=True, auth="user")
    def scheduled_classes_data(self, **kw):
        values = {}
        state = kw.get('sort_by')
        selected_date = kw.get('sort_date')
        current_date = datetime.today().date()
        company_id = [int(company) for company in kw.get('company_id').split('-')]

        if selected_date == 'week':
            start_date = current_date - timedelta(days=current_date.weekday())
            end_date = start_date + timedelta(days=6)

        elif selected_date == 'month':
            start_date = current_date.replace(day=1)
            next_month = current_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)

        elif selected_date == 'year':
            start_date = current_date.replace(month=1, day=1)
            end_date = current_date.replace(month=12, day=31)

        domain = [
            ('class_date', '>=', start_date),
            ('class_date', '<=', end_date),
            ('company_id', 'in', company_id)
        ]
        if state != 'all':
            domain.append(('state', '=', state))

        classes = request.env['wk.class.timetable'].search(domain, order='class_date asc')

        future_classes = classes.filtered(lambda c: c.class_date >= current_date)
        past_classes = classes.filtered(lambda c: c.class_date < current_date)

        past_classes = past_classes.sorted(key=lambda c: c.class_date) 
        ordered_classes = future_classes + past_classes

        values['timetable_ids'] = ordered_classes
        body = request.env['ir.qweb']._render('wk_school_management.scheduled_classes', values)
        return body

    @http.route(['/school_dashboard/enrollment_data'], type='json', auth='user', website=True)
    def enrollment_graph(self, **kw):
        values = []
        selected_date = kw.get('sort_date')
        company_id = [int(cid) for cid in kw.get('company_id', '').split('-') if cid]

        current_date = datetime.today()
        start_date = end_date = current_date

        if selected_date == 'week':
            start_date = current_date - timedelta(days=current_date.weekday())
            end_date = start_date + timedelta(days=6)
        elif selected_date == 'month':
            start_date = current_date.replace(day=1)
            next_month = (start_date + timedelta(days=32)).replace(day=1)
            end_date = next_month - timedelta(days=1)
        elif selected_date == 'year':
            start_date = current_date.replace(month=1, day=1)
            end_date = current_date.replace(month=12, day=31)

        start_str = start_date.strftime('%Y-%m-%d 00:00:00')
        end_str = end_date.strftime('%Y-%m-%d 23:59:59')

        states = ['draft', 'progress', 'complete', 'cancel']
        for state in states:
            count = request.env['student.enrollment'].sudo().search_count([
                ('state', '=', state),
                ('create_date', '>=', start_str),
                ('create_date', '<=', end_str),
                ('company_id', 'in', company_id)])
            values.append(count)
        return values

    @http.route(['/school_dashboard/application_data'], type='json', auth='user', website=True)
    def application_graph(self, **kw):
        values = []
        selected_date = kw.get('sort_date')
        company_id = [int(cid) for cid in kw.get('company_id', '').split('-') if cid]

        current_date = datetime.today()
        start_date = end_date = current_date

        if selected_date == 'week':
            start_date = current_date - timedelta(days=current_date.weekday())
            end_date = start_date + timedelta(days=6)
        elif selected_date == 'month':
            start_date = current_date.replace(day=1)
            next_month = (start_date + timedelta(days=32)).replace(day=1)
            end_date = next_month - timedelta(days=1)
        elif selected_date == 'year':
            start_date = current_date.replace(month=1, day=1)
            end_date = current_date.replace(month=12, day=31)

        start_str = start_date.strftime('%Y-%m-%d 00:00:00')
        end_str = end_date.strftime('%Y-%m-%d 23:59:59')

        states = ['new', 'confirm', 'enroll', 'cancel']
        for state in states:
            count = request.env['wk.application.form'].sudo().search_count([
                ('state', '=', state),
                ('create_date', '>=', start_str),
                ('create_date', '<=', end_str),
                ('company_id', 'in', company_id)
            ])
            values.append(count)
        return values


class CustomerPortal(Controller):

    def _get_student_context(self):
        user = request.env.user
        student_model = request.env['student.student'].sudo()
        parent_model = request.env['res.partner'].sudo()

        parent = parent_model.search([
            ('is_parent', '=', True),
            ('user_ids', 'in', user.id)
        ], limit=1)

        linked_students = student_model.search([
            ('parent_ids.user_ids', 'in', user.id),
            ('active', '=', True)
        ]) if parent else student_model.search([
            ('user_id', '=', user.id),
            ('active', '=', True)
        ], limit=1)

        student_id = request.httprequest.args.get('student_id')

        if not student_id:
            student_id = request.session.get('selected_student_id')

        selected_student = None

        if student_id:
            try:
                student_candidate = student_model.browse(int(student_id))
                if student_candidate in linked_students:
                    selected_student = student_candidate
            except Exception:
                pass

        if not selected_student and linked_students:
            selected_student = linked_students[0]

        if selected_student:
            request.session['selected_student_id'] = selected_student.id
        else:
            request.session.pop('selected_student_id', None)

        return {
            'user': user,
            'parent': parent,
            'linked_students': linked_students,
            'selected_student': selected_student,
        }

    @http.route(['/my/dashboard'], type='http', auth="user", website=True)
    def home(self, **kw):
        context = self._get_student_context()

        if not context['selected_student']:
            return request.render('wk_school_management.student_not_found')

        student = context['selected_student']
        enrollment = student.current_enrollment_id
        grade = student.current_grade_id

        if student and student.current_enrollment_id:
            fee_summary_ids = student.current_enrollment_id.fee_summary_ids
            total_amount = sum(fee_summary.fee for fee_summary in fee_summary_ids)
        else:
            total_amount = 0.0

        timetable_ids = request.env['wk.class.timetable'].sudo().search([
            ('grade_id', '=', grade.id),
            ('class_date', '=', date.today())
        ])
        if timetable_ids and hasattr(timetable_ids[0], 'student_ids'):
            timetable_ids = timetable_ids.filtered(
                lambda t: student.id in t.student_ids.mapped('student_id').ids
            )

        fee_slips = request.env['wk.fee.slip'].sudo().search([
            ('student_id', '=', student.id),
            ('enrollment_id', '=', enrollment.id),
            ('state', 'not in', ('cancel', 'new'))
        ])
        paid_amount = sum(slip.total_amount for slip in fee_slips if slip.state == 'paid')

        notice_ids = request.env['wk.notice.board'].sudo().search([
            ('state', '=', 'active'),
            '|',
            ('visibility', '=', 'all'),
            ('visibility', '=', 'students')
        ])

        values = {
            'school_dashboard': True,
            'parent': bool(context['parent']),
            'linked_students': context['linked_students'],
            'student': student,
            'time_table_ids': timetable_ids,
            'fee_slip_ids': fee_slips,
            'notice_ids': notice_ids,
            'total_amount': total_amount,
            'paid_amount': paid_amount,
            'due_amount': total_amount - paid_amount,
            'currency_id': fee_slips.currency_id,
            'enrollment_value':True if enrollment else False,
        }

        return request.render("wk_school_management.portal_dashboard", values)

    @http.route(['/my/timetables/<model("wk.class.timetable"):timetable_id>'], type='http', auth="user", website=True)
    def portal_my_appointment_detail(self, timetable_id=None, access_token=None, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']

        if not timetable_id or not timetable_id.exists():
            return request.redirect('/my/timetables')

        if selected_student not in linked_students:
            return request.render('wk_school_management.student_not_found')

        lesson_plans = "\n\n".join(timetable_id.lesson_plan_ids.mapped('description'))

        values = {
            'timetable': True,
            'timetable_id': timetable_id,
            'student': selected_student,
            'lesson_plans': lesson_plans,
            'parent': bool(context['parent']),
            'teacher_name': timetable_id.sudo().teacher_id.name
        }
        return request.render("wk_school_management.portal_timetable_form_view", values)

    @http.route(['/my/timetables', '/my/timetables/page/<int:page>'], type='http', auth="user", website=True)
    def portal_student_timetable(self, page=0, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        values = {
            'timetable': True,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student
        }

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        timetable_domain = [
            ('grade_id', '=', selected_student.current_grade_id.id),
            ('class_date', '>=', date.today())
        ]
        all_timetables = request.env['wk.class.timetable'].sudo().search(timetable_domain, order='class_date')

        if all_timetables and hasattr(all_timetables[0], 'student_ids'):
            all_timetables = all_timetables.filtered(
                lambda t: selected_student.id in t.student_ids.mapped('student_id').ids
            )

        pager = request.website.pager(
            url="/my/timetables",
            total=len(all_timetables),
            page=page,
            step=10,
            url_args={'student_id': selected_student.id, 'view_mode': kw.get('view_mode', '')}
        )

        paginated_timetables = all_timetables[pager['offset']: pager['offset'] + 10]
        values['time_table_ids'] = paginated_timetables

        view_mode = kw.get('view_mode')
        if view_mode == "list":
            values['pager'] = pager
            return request.render("wk_school_management.portal_timetable_list_view", values)

        return request.render("wk_school_management.portal_timetable", values)

    @http.route(['/my/assignments', '/my/assignments/page/<int:page>'], type='http', auth="user", website=True)
    def portal_student_assignments(self, page=0, search=None, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        values = {
            'assignment': True,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student
        }

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        domain = [
            ('student_id', '=', selected_student.id),
            ('grade_id', '=', selected_student.current_grade_id.id)
        ]

        if search:
            if search in ('new', 'submit', 'evaluate'):
                domain += [('state', '=', search)]
            else:
                domain += [('assignment_id.name', 'ilike', search)]

        assignment_allocated = request.env['wk.student.assignment'].sudo().search(
            domain, order='create_date desc')

        pager = request.website.pager(
            url='/my/assignments',
            total=len(assignment_allocated),
            page=page,
            step=10,
        )

        offset = pager['offset']
        assignment_allocated = assignment_allocated[offset: offset + 10]

        values['student_assignment_ids'] = assignment_allocated
        values['pager'] = pager
        return request.render("wk_school_management.portal_assignment_list_view", values)

    @http.route(['/my/assignment/<model("wk.student.assignment"):assignment_id>'], type='http', auth="user", website=True)
    def portal_my_assignment_detail(self, assignment_id=None, **kw):
        student_assignment = request.env['wk.student.assignment'].sudo().browse(assignment_id.id)
        if not student_assignment.exists():
            return request.redirect('/my/assignments')

        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        values = {
            'assignment': True,
            'assignment_id': student_assignment,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student
        }

        image_type_attachment = student_assignment.attachment_ids.filtered(
            lambda a: a.document_type == 'image')
        other_attachments = student_assignment.attachment_ids - image_type_attachment
        submit_attachement = student_assignment.submitted_assignment_attachment
        submit_attachement_type = student_assignment.submit_attachment_type

        if image_type_attachment:
            values['image_type_attachment'] = image_type_attachment
        if other_attachments:
            values['other_attachments'] = other_attachments
        if submit_attachement:
            values['submit_attachement'] = submit_attachement
        if submit_attachement_type:
            values['submit_attachement_type'] = submit_attachement_type

        return request.render("wk_school_management.portal_assignment_form_view", values)

    @http.route('/assignment/submit', type='json', website='True', auth="public", csrf=True)
    def assignment_submit(self, **kw):

        assignment_id = kw.pop('assignment_id')
        description = kw.pop('description')
        attachement = kw.pop('attachement')
        filename = kw.pop('fileName')
        attachment_type_id = kw.pop('attachment_type_id')

        dataURL = attachement.split(",")
        mime_type, base64_data = dataURL
        document_data = base64.b64decode(base64_data)
        student_assignment = request.env['wk.student.assignment'].sudo().browse(int(assignment_id))

        values = {
            'submitted_assignment_attachment': base64.b64encode(document_data).decode('utf-8'),
            'filename': filename,
            'submit_comment': description,
            'state': 'submit',
            'submit_attachment_type': attachment_type_id
        }
        student_assignment.write(values)

        return values

    @http.route('/download/attachment/<int:record_id>', type='http', auth='public')
    def download_attachment(self, record_id, submitted_attachment=False):
        if submitted_attachment:
            record = request.env['wk.student.assignment'].sudo().browse(
                record_id)
            if not record or not record.submitted_assignment_attachment:
                return request.not_found()
            filecontent = base64.b64decode(
                record.submitted_assignment_attachment)
            filename = record.filename
        else:
            record = request.env['wk.assignment.attachment'].sudo().browse(
                record_id)
            if not record or not record.document:
                return request.not_found()

            filecontent = base64.b64decode(record.document)
            filename = record.filename

        return request.make_response(filecontent,
                                     headers=[('Content-Type', 'application/octet-stream'),
                                              ('Content-Disposition', f'attachment; filename={filename}'),])

    @http.route(['/my/service-hour'], type='http', auth="user", website=True)
    def portal_service_hour(self, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')
        values = {
            'service_hours': True,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student
        }

        enrollment_record = selected_student.current_enrollment_id
        supervisor_ids = request.env['hr.employee'].sudo().search([('is_supervisor', '=', True)])

        if enrollment_record:
            values['service_hour_ids'] = enrollment_record.service_hour_ids
        if supervisor_ids:
            values['supervisor_ids'] = supervisor_ids

        return request.render("wk_school_management.portal_service_hour", values)

    @http.route('/servicehour/submit', type='json', website='True', auth="public", csrf=True)
    def service_hour_submit(self, **kw):
        name = kw.pop('name')
        start_time = kw.pop('start_time')
        total_hours = kw.pop('total_hours')
        supervisor_id = kw.pop('supervisor_id')
        student_id = request.session.get('selected_student_id')
        comment = kw.pop('comment')

        time_format = '%Y-%m-%dT%H:%M'
        start_time = datetime.strptime(start_time, time_format)

        vals = {
            'name': name,
            'start_time': start_time,
            'total_hours': total_hours,
            'supervisor_id': int(supervisor_id) if supervisor_id != '0' else False,
            'student_id': int(student_id),
            'comment': comment
        }
        record = request.env['wk.service.hours'].sudo().create(vals)
        return record

    @http.route(['/my/service-hour/<model("wk.service.hours"):service_hour_id>'], type='http', auth="user", website=True)
    def portal_service_hour_detail(self, service_hour_id=None, **kw):
        service_hour_record = request.env['wk.service.hours'].sudo().browse(service_hour_id.id)
        if not service_hour_record.exists():
            return request.redirect('/my/service-hour')

        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')
        values = {
            'service_hours': True,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student,
            'service_hour_id': service_hour_record
        }
        return request.render("wk_school_management.portal_service_hour_form_view", values)

    @http.route(['/my/attendances', '/my/attendances/page/<int:page>'], type='http', auth="user", website=True)
    def portal_student_attendance(self, page=0, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        values = {
            'attendance': True,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student
        }

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        entry_attendances = request.env['wk.student.attendance'].sudo().search([
            ('student_id', '=', selected_student.id)])

        pager = request.website.pager(
            url='/my/attendances',
            total=len(entry_attendances),
            page=page,
            step=10,
            url_args={'view_mode': 'list'}
        )

        offset = pager['offset']
        paginated_attendances = entry_attendances[offset: offset + 10]

        values['entry_attendances'] = paginated_attendances

        view_mode = kw.get('view_mode')
        if view_mode == "list":
            values['pager'] = pager
            return request.render("wk_school_management.portal_attendance_list_view", values)

        return request.render("wk_school_management.portal_attendance", values)

    @http.route(['/my/student/attendance'], type='json', auth="user", website=True, csrf=False)
    def portal_my_attendance(self, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        parent = context['parent']
        attendance_list = []
        entry_attendances = request.env['wk.student.attendance'].sudo().search([
            ('student_id', '=', selected_student.id)
        ])

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        public_holidays = request.env['wk.student.public.holidays'].sudo().search([])

        for holiday in public_holidays:
            attendance_list.append({
                'date': holiday.date,
                'state': 'public_holiday',
                'className': 'fc-event-public_holiday',
                'extendedProps': {'name': holiday.name},
                'parent': bool(parent),
            })

        for attendance in entry_attendances:
            if attendance.attendance_state in ['present', 'absent']:
                attendance_list.append({
                    'date': attendance.attendance_date,
                    'state': attendance.attendance_state,
                    'className': f'fc-event-{attendance.attendance_state}',
                })

        return {'data': attendance_list}

    @http.route(['/my/attendance/<model("wk.student.attendance"):attendance_id>'], type='http', auth="user", website=True)
    def portal_my_attendance_detail(self, attendance_id=None, **kw):
        student_attendance = request.env['wk.student.attendance'].sudo().browse(attendance_id.id)
        if not student_attendance.exists():
            return request.redirect('/my/attendances')

        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')
        values = {
            'attendance': True,
            'student_attendance': student_attendance,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student,
        }

        class_attendances = request.env['wk.student.class.attendance'].sudo().search([
            ('student_attendance_id', '=', student_attendance.id)
        ])

        if class_attendances:
            values['class_attendances'] = class_attendances

        return request.render("wk_school_management.portal_attendance_form_view", values)

    @http.route(['/my/attendances/detail'], type='http', auth="user", website=True)
    def portal_my_attendance_by_date(self, date=None, **kw):
        if not date:
            return request.redirect('/my/attendances')
        try:
            date_obj = fields.Date.from_string(date)
        except ValueError:
            return request.redirect('/my/attendances')

        context = self._get_student_context()
        selected_student = context['selected_student']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        student_attendance = request.env['wk.student.attendance'].sudo().search([
            ('attendance_date', '=', date_obj),
            ('student_id', '=', selected_student.id)
        ], limit=1)

        if not student_attendance:
            return request.redirect('/my/attendances')

        return request.redirect('/my/attendance/%d' % student_attendance.id)

    @http.route(['/my/enrollments'], type='http', auth="user", website=True)
    def portal_student_enrollments(self, page=0, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        values = {
            'enrollment': True,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student
        }

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        enrollments = request.env['student.enrollment'].sudo().search([
            ('student_id', '=', selected_student.id)
        ])
        values['enrollment_ids'] = enrollments

        return request.render("wk_school_management.portal_enrollments", values)

    @http.route(['/my/enrollment/<model("student.enrollment"):enrollment_id>'], type='http', auth="user", website=True)
    def portal_my_enrollment_detail(self, enrollment_id=None, **kw):
        enrollment_record = request.env['student.enrollment'].sudo().browse(enrollment_id.id)
        if not enrollment_record.exists():
            return request.redirect('/my/enrollments')

        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        values = {
            'enrollment': True,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student,
            'enrollment_id': enrollment_record
        }

        if enrollment_record.scholarship_ids:
            values['scholarship'] = True
            values['scholarship_ids'] = enrollment_record.scholarship_ids

        return request.render("wk_school_management.portal_enrollment_form_view", values)

    @http.route(['/my/fee-summary'], type='http', auth="user", website=True)
    def portal_student_fee_summary(self, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        values = {
            'fee_summary': True,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student
        }

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        if selected_student and selected_student.current_enrollment_id:
            fee_summary_ids = selected_student.current_enrollment_id.fee_summary_ids
            total_amount = sum(fee_summary.fee for fee_summary in fee_summary_ids)
        else:
            total_amount = 0.0

        values['total_amount'] = total_amount

        fee_slips = request.env['wk.fee.slip'].sudo().search([
            ('student_id', '=', selected_student.id),
            ('enrollment_id', '=', selected_student.current_enrollment_id.id),
            ('state', 'not in', ('cancel', 'new'))
        ])
        paid_amount = sum(slip.total_amount for slip in fee_slips if slip.state == 'paid')
        values['paid_amount'] = paid_amount
        values['due_amount'] = total_amount - paid_amount
        values['fee_slip_ids'] = fee_slips
        values['currency_id'] = fee_slips.currency_id

        return request.render("wk_school_management.portal_fee_summary", values)

    @http.route(['/my/fee/summary/<model("wk.fee.slip"):slip_id>'], type='http', auth="user", website=True)
    def portal_my_fee_detail(self, slip_id=None, **kw):
        slip_id_record = request.env['wk.fee.slip'].sudo().browse(slip_id.id)
        if not slip_id_record.exists():
            return request.redirect('/my/fee-summary')

        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        values = {
            'fee_summary': True,
            'slip_id': slip_id_record,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student
        }

        slip_line_ids = request.env['wk.fee.slip.lines'].sudo().search([
            ('fee_slip_id', '=', slip_id.id)
        ])
        values['slip_line_ids'] = slip_line_ids

        return request.render("wk_school_management.portal_fee_summary_form_view", values)

    @http.route(['/my/grade-summary'], type='http', auth="user", website=True)
    def portal_student_grade_summary(self, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        values = {
            'grade_summary': True,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student
        }
        return request.render("wk_school_management.portal_grade_summary", values)

    @http.route(['/my/transcripts'], type='http', auth="user", website=True)
    def portal_student_transcripts(self, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        values = {
            'transcript': True,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student
        }

        return request.render("wk_school_management.portal_grade_transcript", values)

    @http.route('/my/transcript/download/<int:student_id>/<int:session_id>', type='http', auth="user")
    def download_transcript(self, student_id=None, session_id=None, **kwargs):

        student = request.env['student.student'].sudo().browse(int(student_id))
        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf('wk_school_management.student_transcript_print', [student.id],
                                                                       {'session_id': session_id,
                                                                        'student_id': student_id}
                                                                       )[0]

        filename = f'{student.name}-Transcript.pdf'
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', f'attachment; filename="{filename}"')
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route(['/my/discipline'], type='http', auth="user", website=True)
    def portal_student_discipline(self, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        values = {
            'discipline': True,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student
        }

        enrollment_record = selected_student.current_enrollment_id
        if enrollment_record:
            values['student_discipline_ids'] = enrollment_record.discipline_ids

        return request.render("wk_school_management.portal_discipline", values)

    @http.route(['/my/discipline/<model("wk.student.discipline"):discipline_id>'], type='http', auth="user", website=True)
    def portal_my_discipline_detail(self, discipline_id=None, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        discipline_record = request.env['wk.student.discipline'].sudo().browse(discipline_id.id)
        if not discipline_record.exists():
            return request.redirect('/my/discipline')

        values = {
            'discipline': True,
            'parent': bool(parent),
            'student': selected_student
        }
        if discipline_record:
            values['student_discipline_id'] = discipline_record
        return request.render("wk_school_management.portal_discipline_form_view", values)

    @http.route(['/my/timesheet', '/my/timesheet/page/<int:page>'], type='json', auth="user", website=True, csrf=False)
    def portal_my_timesheet(self, page=1, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        if not selected_student:
            return request.render('wk_school_management.student_not_found')
        time_table_details = request.env['wk.class.timetable'].sudo().search(
            [('grade_id', '=', selected_student.current_grade_id.id)], order='class_date'
        )
        time_table_details = time_table_details.filtered(
            lambda m: selected_student.id in m.student_ids.mapped('student_id').ids
        )
        Scheduled_time_table = []
        if time_table_details:
            for time_table in time_table_details:
                color = ''
                if time_table.state == "draft":
                    color = '#bbcffb'
                elif time_table.state == "running":
                    color = '#bbcffb'
                elif time_table.state == "complete":
                    color = '#bbcffb'
                timetable_cal_dict = {}
                start_time = time_table.get_slot_time(
                    time_table.timeslot_id.start_time, calendar_time=True)
                end_time = time_table.get_slot_time(
                    time_table.timeslot_id.end_time, calendar_time=True)
                app_cal_start = f"{time_table.class_date.strftime('%Y-%m-%d')}T{start_time}"
                app_cal_end = f"{time_table.class_date.strftime('%Y-%m-%d')}T{end_time}"
                class_title = f"{time_table.subject_id.name}-({time_table.location_id.name})"
                timetable_cal_dict['title'] = class_title
                timetable_cal_dict['start'] = app_cal_start
                timetable_cal_dict['end'] = app_cal_end
                timetable_cal_dict['color'] = color
                timetable_cal_dict['id'] = time_table.id
                timetable_cal_dict['extendedProps'] = {
                    'date': time_table.class_date,
                    'start_time': time_table.timeslot_id.float_to_time(time_table.timeslot_id.start_time),
                    'end_time': time_table.timeslot_id.float_to_time(time_table.timeslot_id.end_time),
                    'location': time_table.location_id.name,
                },
                Scheduled_time_table.append(timetable_cal_dict)

        return {'data': Scheduled_time_table}

    @http.route(['/my/notice/board'], type='http', auth="user", website=True)
    def portal_student_notice_board(self, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        values = {
            'notice_board': True,
            'parent': parent,
            'student': selected_student
        }
        notice_ids = request.env['wk.notice.board'].sudo().search([
            ('state', '=', 'active'),
            '|',
            ('visibility', '=', 'all'),
            ('visibility', '=', 'students')
        ])
        if notice_ids:
            values['notice_ids'] = notice_ids

        return request.render("wk_school_management.portal_notice_board", values)

    @http.route(['/my/notice/board/<model("wk.notice.board"):notice_id>'], type='http', auth="user", website=True)
    def portal_my_notice_detail(self, notice_id=None, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        notice_record = request.env['wk.notice.board'].sudo().browse(notice_id.id)
        if not notice_record.exists():
            return request.redirect('/my/notice/board')

        values = {
            'notice_board': True,
            'parent': parent,
            'student': selected_student,
            'notice_id': notice_record
        }
        return request.render("wk_school_management.portal_notice_form_view", values)

    @http.route(['/my/fee_slip/payment'], type='http', auth="public", website=True, methods=['POST'], csrf=True)
    def portal_my_fee_slip_payment(self, **kw):
        slip_id = kw.pop('slip_id')
        slip_record = request.env['wk.fee.slip'].sudo().browse(int(slip_id))
        PaymentLinkWizard = request.env['payment.link.wizard']
        context = {
            'res_model': 'wk.fee.slip',
            'res_id': slip_record.id,
            'amount': slip_record.total_amount,
            'currency_id': slip_record.currency_id.id,
            'partner_id': slip_record.student_id.user_id.partner_id.id,
        }
        payment_wizard = PaymentLinkWizard.sudo().with_context(context).create(context)
        payment_wizard._compute_link()
        payment_link = payment_wizard.link

        return request.redirect(payment_link)

    @http.route(['/my/fee/summary/terms/<int:slip_id>'], type='http', auth="public", website=True)
    def portal_my_fee_terms(self, slip_id=None, **kw):
        slip_id_record = request.env['wk.fee.slip'].sudo().browse(int(slip_id))
        if not slip_id_record.exists():
            return request.redirect('/my/fee-summary')

        context = self._get_student_context()
        selected_student = context['selected_student']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        values = {
            'fee_summary': True,
            'slip_id': slip_id_record,
            'description': slip_id_record.description,
            'parent': parent,
            'student': selected_student
        }
        return request.render("wk_school_management.portal_fee_summary_conditions_view", values)

    @http.route('/my/assignments/<string:assignment_type>/<int:subject_id>', auth='user', type='http', website=True)
    def subject_assignments(self, assignment_type, subject_id, search=None, page=0, **kwargs):
        subject = request.env['wk.grade.subjects'].sudo().browse(subject_id)

        user = request.env.user
        student = request.env['student.student'].sudo().search([('user_id', '=', user.id)])

        domain = [('student_id', '=', student.id), ('subject_id', '=', subject.id)]

        if assignment_type == 'incomplete':
            domain.append(('state', '=', 'new'))
        elif assignment_type == 'completed':
            domain += ['|', ('state', '=', 'submit'), ('state', '=', 'evaluate')]

        if search:
            if search in ('new', 'submit', 'evaluate'):
                domain += [('state', '=', search)]
            else:
                domain += [('assignment_id.name', 'ilike', search)]


        assignments = request.env['wk.student.assignment'].sudo().search(domain)
        values = {
            'assignment': True,
        }
        if student:
            values['student'] = student

        pager = request.website.pager(
            url=f'/my/assignments/{assignment_type}/{subject_id}',
            total=len(assignments),
            page=page,
            step=10,
        )

        offset = pager['offset']
        assignments = assignments[offset: offset + 10]
        if assignments:
            values['student_assignment_ids'] = assignments

        values['pager'] = pager
        return request.render("wk_school_management.portal_grade_assignment_list_views", values)

    @http.route('/my/fee/summary', auth='public', type='http', website=True)
    def fee_payment(self, **kw):
        slip_id = next(iter(kw))
        slip_record = request.env['wk.fee.slip'].sudo().browse(int(slip_id))
        if not slip_record.exists():
            return request.redirect('/web/login')

        context = self._get_student_context()
        selected_student = context['selected_student']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')
        values = {
            'fee_summary': True,
            'slip_id': slip_record,
            'student': selected_student,
            'parent': bool(parent)
        }
        slip_line_ids = request.env['wk.fee.slip.lines'].sudo().search(
            [('fee_slip_id', '=', int(slip_id))]
        )
        if slip_line_ids:
            values['slip_line_ids'] = slip_line_ids
        return request.render("wk_school_management.public_fee_summary_form_view", values)
    
    @http.route(['/my/transport', '/my/transport/page/<int:page>'], type='http', auth="user", website=True)
    def portal_student_transport(self, page=0, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        linked_students = context['linked_students']
        parent = context['parent']

        values = {
            'transport': True,
            'parent': bool(parent),
            'linked_students': linked_students,
            'student': selected_student
        }

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        # Get all routes for the student's school/company
        transport_lines_ids = request.env['transport.trip.line'].sudo().search([
            ('student_id', '=', selected_student.id),
            ('company_id', '=', selected_student.company_id.id),
        ], order = 'trip_id desc')
        
        # transport_lines_ids = transport_lines_ids.filtered(lambda line: line.trip_id.state != 'cancelled')
        
        values['transport_lines_ids'] = transport_lines_ids
        
        student_route_stop = selected_student.route_id.route_stop_ids.filtered(lambda r: r.location_id == selected_student.location_id)
        values['student_route_stop'] = student_route_stop

        return request.render("wk_school_management.portal_transport", values)
    
    @http.route(['/my/transport/<model("transport.trip.line"):line_id>'], type='http', auth="user", website=True)
    def portal_student_transport_detail(self, line_id=None, **kw):
        context = self._get_student_context()
        selected_student = context['selected_student']
        parent = context['parent']

        if not selected_student:
            return request.render('wk_school_management.student_not_found')

        values = {
            'transport': True,
            'parent': bool(parent),
            'student': selected_student,
            'line_id': line_id
        }

        return request.render("wk_school_management.portal_transport_form_view", values)


class MailControllerInherit(MailController):

    @http.route('/mail/view', type='http', auth='public')
    def mail_action_view(self, model=None, res_id=None, access_token=None, **kw):
        if model == "wk.fee.slip":
            slip_id = int(res_id)
            slip_record = request.env['wk.fee.slip'].sudo().browse(slip_id)
            base_url = slip_record.get_base_url()
            if access_token == slip_record.access_token:
                link = f"{base_url}/my/fee/summary?{slip_id}&access_token={slip_record.access_token}"
                return request.redirect(link)
            else:
                return request.redirect('/web/login')

        return super().mail_action_view(model, res_id, access_token, **kw)
