# -*- coding: utf-8 -*-

from odoo import http, models, fields, api, _
from odoo.http import request
from odoo.exceptions import ValidationError


class ObeCloPloMatrixController(http.Controller):
    """Controller for CLO-PLO Matrix Web View"""

    @http.route('/obe/clo_plo_matrix', type='http', auth='user', website=True)
    def matrix_selector(self, **kwargs):
        """Display matrix selector page"""
        courses = request.env['obe.course'].search([('active', '=', True)])
        programs = request.env['obe.academic.program'].search([('active', '=', True)])
        
        return request.render('obe_core.clo_plo_matrix_selector_page', {
            'courses': courses,
            'programs': programs,
        })

    @http.route('/obe/clo_plo_matrix/view', type='http', auth='user', website=True)
    def matrix_view(self, course_id=None, program_id=None, offering_id=None, **kwargs):
        """Display CLO-PLO mapping matrix"""
        
        if not course_id or not program_id:
            return request.redirect('/obe/clo_plo_matrix')
        
        course_id = int(course_id)
        program_id = int(program_id)
        offering_id = int(offering_id) if offering_id else None
        
        # Get course and program
        course = request.env['obe.course'].browse(course_id)
        program = request.env['obe.academic.program'].browse(program_id)
        
        if not course.exists() or not program.exists():
            return request.redirect('/obe/clo_plo_matrix')
        
        # Get CLOs
        clo_domain = [('course_id', '=', course_id), ('active', '=', True)]
        if offering_id:
            clo_domain.append(('offering_id', '=', offering_id))
        clos = request.env['obe.clo'].search(clo_domain, order='sequence, name')
        
        # Get PLOs for the program
        plos = request.env['obe.plo'].search([
            ('program_id', '=', program_id),
            ('active', '=', True)
        ], order='sequence, name')
        
        # Get active mappings
        mapping_domain = [
            ('course_id', '=', course_id),
            ('program_id', '=', program_id),
            ('state', '=', 'active'),
            ('active', '=', True)
        ]
        mappings = request.env['obe.clo.plo.mapping'].search(mapping_domain)
        
        # Build matrix data
        matrix_data = {}
        strength_counts = {'1': 0, '2': 0, '3': 0, '0': 0}
        
        for mapping in mappings:
            for plo in mapping.plo_ids:
                key = f"{mapping.clo_id.id}_{plo.id}"
                matrix_data[key] = mapping.strength
                strength_counts[mapping.strength] = strength_counts.get(mapping.strength, 0) + 1
        
        # Calculate coverage
        total_possible = len(clos) * len(plos)
        total_mapped = len([v for v in matrix_data.values() if v != '0'])
        coverage_percentage = round((total_mapped / total_possible * 100), 1) if total_possible > 0 else 0
        
        # Calculate statistics
        total_mappings = len(matrix_data)
        strength_high = strength_counts.get('3', 0)
        strength_medium = strength_counts.get('2', 0)
        strength_low = strength_counts.get('1', 0)
        strength_none = total_possible - total_mapped
        
        # Calculate average strength
        strength_values = [int(v) for v in matrix_data.values() if v != '0']
        average_strength = round(sum(strength_values) / len(strength_values), 1) if strength_values else 0
        
        # PLO coverage analysis
        plo_coverage = {}
        for plo in plos:
            plo_mappings = [v for k, v in matrix_data.items() if k.endswith(f'_{plo.id}') and v != '0']
            plo_coverage[plo.id] = len(plo_mappings)
        
        plos_fully_covered = len([c for c in plo_coverage.values() if c >= len(clos) * 0.7])
        plos_partially_covered = len([c for c in plo_coverage.values() if 0 < c < len(clos) * 0.7])
        plos_not_covered = len([c for c in plo_coverage.values() if c == 0])
        
        return request.render('obe_core.clo_plo_matrix_view', {
            'course': course,
            'program': program,
            'clos': clos,
            'plos': plos,
            'matrix_data': matrix_data,
            'total_clos': len(clos),
            'total_plos': len(plos),
            'total_mappings': total_mappings,
            'coverage_percentage': coverage_percentage,
            'strength_high': strength_high,
            'strength_medium': strength_medium,
            'strength_low': strength_low,
            'strength_none': strength_none,
            'average_strength': average_strength,
            'plos_fully_covered': plos_fully_covered,
            'plos_partially_covered': plos_partially_covered,
            'plos_not_covered': plos_not_covered,
        })

    @http.route('/obe/clo_plo_matrix/export', type='http', auth='user')
    def matrix_export_csv(self, course_id=None, program_id=None, **kwargs):
        """Export matrix to CSV"""
        import csv
        import io
        
        if not course_id or not program_id:
            return request.redirect('/obe/clo_plo_matrix')
        
        course_id = int(course_id)
        program_id = int(program_id)
        
        course = request.env['obe.course'].browse(course_id)
        program = request.env['obe.academic.program'].browse(program_id)
        
        clos = request.env['obe.clo'].search([
            ('course_id', '=', course_id),
            ('active', '=', True)
        ], order='sequence, name')
        
        plos = request.env['obe.plo'].search([
            ('program_id', '=', program_id),
            ('active', '=', True)
        ], order='sequence, name')
        
        mappings = request.env['obe.clo.plo.mapping'].search([
            ('course_id', '=', course_id),
            ('program_id', '=', program_id),
            ('state', '=', 'active')
        ])
        
        matrix_data = {}
        for mapping in mappings:
            for plo in mapping.plo_ids:
                key = f"{mapping.clo_id.id}_{plo.id}"
                matrix_data[key] = mapping.strength
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['CLO-PLO Mapping Matrix'])
        writer.writerow([f'Course: {course.code} - {course.name}'])
        writer.writerow([f'Program: {program.code} - {program.name}'])
        writer.writerow([])
        
        # Matrix header
        header = ['CLO / PLO'] + [plo.name for plo in plos]
        writer.writerow(header)
        
        # Matrix rows
        for clo in clos:
            row = [clo.name]
            for plo in plos:
                strength = matrix_data.get(f"{clo.id}_{plo.id}", '0')
                row.append(strength if strength != '0' else '-')
            writer.writerow(row)
        
        # Prepare response
        output.seek(0)
        filename = f"CLO_PLO_Matrix_{course.code}_{program.code}.csv"
        
        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'text/csv'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )


# Extended model with matrix generation methods
class ObeCloPloMatrix(models.TransientModel):
    """Extended matrix model with helper methods"""
    _inherit = 'obe.clo.plo.matrix'

    def action_view_matrix(self):
        """Open matrix in web view"""
        self.ensure_one()
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = f"{base_url}/obe/clo_plo_matrix/view?course_id={self.course_id.id}&program_id={self.program_id.id}"
        
        if self.offering_id:
            url += f"&offering_id={self.offering_id.id}"
        
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_print_matrix(self):
        """Generate PDF report"""
        self.ensure_one()
        return self.env.ref('obe_core.action_report_clo_plo_matrix').report_action(self)

    def action_export_csv(self):
        """Export matrix to CSV"""
        self.ensure_one()
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = f"{base_url}/obe/clo_plo_matrix/export?course_id={self.course_id.id}&program_id={self.program_id.id}"
        
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def get_matrix_data(self):
        """Get matrix data for QWeb template"""
        self.ensure_one()
        
        # Get CLOs
        clo_domain = [('course_id', '=', self.course_id.id), ('active', '=', True)]
        if self.offering_id:
            clo_domain.append(('offering_id', '=', self.offering_id.id))
        clos = self.env['obe.clo'].search(clo_domain, order='sequence, name')
        
        # Get PLOs
        plos = self.env['obe.plo'].search([
            ('program_id', '=', self.program_id.id),
            ('active', '=', True)
        ], order='sequence, name')
        
        # Get mappings
        mappings = self.env['obe.clo.plo.mapping'].search([
            ('course_id', '=', self.course_id.id),
            ('program_id', '=', self.program_id.id),
            ('state', '=', 'active')
        ])
        
        # Build matrix
        matrix_data = {}
        strength_counts = {'1': 0, '2': 0, '3': 0}
        
        for mapping in mappings:
            for plo in mapping.plo_ids:
                key = f"{mapping.clo_id.id}_{plo.id}"
                matrix_data[key] = mapping.strength
                strength_counts[mapping.strength] = strength_counts.get(mapping.strength, 0) + 1
        
        # Calculate statistics
        total_possible = len(clos) * len(plos)
        total_mapped = len([v for v in matrix_data.values() if v != '0'])
        coverage = round((total_mapped / total_possible * 100), 1) if total_possible > 0 else 0
        
        strength_values = [int(v) for v in matrix_data.values() if v != '0']
        avg_strength = round(sum(strength_values) / len(strength_values), 1) if strength_values else 0
        
        # PLO coverage
        plo_coverage = {}
        for plo in plos:
            plo_mappings = [v for k, v in matrix_data.items() if k.endswith(f'_{plo.id}') and v != '0']
            plo_coverage[plo.id] = len(plo_mappings)
        
        return {
            'course': self.course_id,
            'program': self.program_id,
            'clos': clos,
            'plos': plos,
            'matrix_data': matrix_data,
            'total_clos': len(clos),
            'total_plos': len(plos),
            'total_mappings': len(matrix_data),
            'coverage_percentage': coverage,
            'strength_high': strength_counts.get('3', 0),
            'strength_medium': strength_counts.get('2', 0),
            'strength_low': strength_counts.get('1', 0),
            'strength_none': total_possible - total_mapped,
            'average_strength': avg_strength,
            'plos_fully_covered': len([c for c in plo_coverage.values() if c >= len(clos) * 0.7]),
            'plos_partially_covered': len([c for c in plo_coverage.values() if 0 < c < len(clos) * 0.7]),
            'plos_not_covered': len([c for c in plo_coverage.values() if c == 0]),
        }


class IrActionsReport(models.Model):
    """Override to inject data for matrix report"""
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, res_ids=None, data=None):
        """Inject matrix data for CLO-PLO matrix report"""
        if self.report_name == 'obe_core.clo_plo_matrix_view':
            matrix = self.env['obe.clo.plo.matrix'].browse(res_ids)
            if matrix:
                data = matrix.get_matrix_data()
                return super()._render_qweb_pdf(res_ids, data)
        return super()._render_qweb_pdf(res_ids, data)