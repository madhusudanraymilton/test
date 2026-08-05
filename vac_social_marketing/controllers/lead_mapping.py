# -*- coding: utf-8 -*-
import re


LABEL_TARGETS = {
    'areyouacurrentclientofvac': 'is_current_client',
    'areyouacurrentclient': 'is_current_client',
    'areyouaveteran': 'is_veteran',
    'areyouausveteran': 'is_veteran',
    'firstname': 'first_name',
    'lastname': 'last_name',
    'fullname': 'name',
    'phonenumber': 'mobile',
    'mobilenumber': 'mobile',
    'whatsappnumber': 'whatsapp_number',
    'emailaddress': 'email',
    'dateofbirth': 'birthday',
    'currentphysicaladdress': 'physical_address',
    'areyoubringingaplusone': 'is_bringing_plus_one',
    'branchofservice': 'branch_service_id',
    'currentvadisabilityrating': 'current_va_disability_rating',
    'doyouhaveacopyofyourdd214': 'has_dd214_copy',
    'doyouhaveaccesstoyourdd214': 'has_dd214_access',
}

BOOLEAN_FIELDS = {
    'is_current_client',
    'is_veteran',
    'is_bringing_plus_one',
    'has_dd214_copy',
    'has_dd214_access',
}

FLOAT_FIELDS = {
    'current_va_disability_rating',
}

MERGE_FIELDS = {
    'name',
    'notes',
}


def normalize_label(label):
    return re.sub(r'[^a-z0-9]+', '', (label or '').lower())


def parse_bool(value):
    normalized = (value or '').strip().lower()
    return normalized in {'1', 'true', 'yes', 'y', 'on', 'checked'}


def parse_float(value):
    if value in (None, ''):
        return None
    cleaned = re.sub(r'[^0-9.\-]+', '', str(value))
    if not cleaned:
        return None
    # Extract the first number if there are multiple parts (e.g., "10-" -> 10)
    parts = cleaned.split('-')
    try:
        return float(parts[0])
    except ValueError:
        return None


def resolve_branch_service(env, value):
    if not value:
        return None

    try:
        service_id = int(value)
    except (ValueError, TypeError):
        service_id = None

    service_model = env['branch.service'].sudo()
    if service_id:
        service = service_model.browse(service_id)
        if service.exists():
            return service

    return service_model.search([('name', '=', value)], limit=1)


def infer_target_field(field):
    normalized_label = normalize_label(field.label)

    if normalized_label == 'firstname':
        return 'first_name'
    if normalized_label == 'lastname':
        return 'last_name'

    if field.maps_to == 'branch_service':
        return 'branch_service_id'
    if field.maps_to and field.maps_to != 'none':
        return field.maps_to
    return LABEL_TARGETS.get(normalized_label)


def route_registration_value(env, field, value, lead_vals, custom_answers):
    target = infer_target_field(field)

    if not target:
        custom_answers[str(field.id)] = {
            'label': field.label,
            'type': field.field_type,
            'value': value,
        }
        return

    if target == 'branch_service_id':
        service = resolve_branch_service(env, value)
        if service:
            lead_vals['branch_service_id'] = service.id
        return

    if target in BOOLEAN_FIELDS:
        lead_vals[target] = parse_bool(value)
        return

    if target in FLOAT_FIELDS:
        parsed = parse_float(value)
        if parsed is not None:
            lead_vals[target] = parsed
        return

    if target in MERGE_FIELDS and lead_vals.get(target) and value:
        lead_vals[target] = f"{lead_vals[target]} {value}".strip()
        return

    if value not in (None, ''):
        lead_vals[target] = value


def finalize_lead_values(lead_vals):
    first_name = (lead_vals.get('first_name') or '').strip()
    last_name = (lead_vals.get('last_name') or '').strip()
    if not lead_vals.get('name') and (first_name or last_name):
        lead_vals['name'] = ' '.join(part for part in [first_name, last_name] if part)
    return lead_vals
