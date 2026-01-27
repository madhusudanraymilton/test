from odoo import http
from odoo.http import request
import json
import jwt
import datetime
from functools import wraps

# ================= JWT CONFIG =================
ALGORITHM = "HS256"
TOKEN_EXP_HOURS = 2  # token expires in 2 hours
SECURITY_KEY="asdfghjkkkkkl83409"

def generate_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXP_HOURS)
    }
    token = jwt.encode(payload, SECURITY_KEY, algorithm=ALGORITHM)
    return token

def verify_token(token):
    try:
        payload = jwt.decode(token, SECURITY_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        # Token expired
        return None
    except jwt.InvalidTokenError:
        # Token invalid
        return None

def jwt_required(func):
    """Decorator to enforce JWT authentication on routes"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.httprequest.headers.get("Authorization")
        if not auth_header:
            return request.make_json_response(
                {"status": "error", "message": "Authorization header missing"},
                status=401
            )

        try:
            token = auth_header.split(" ")[1]
        except IndexError:
            return request.make_json_response(
                {"status": "error", "message": "Invalid token format. Use: Bearer <token>"},
                status=401
            )

        payload = verify_token(token)
        if not payload:
            return request.make_json_response(
                {"status": "error", "message": "Invalid or expired token"},
                status=401
            )

        # Verify user exists and is active
        user = request.env['res.users'].sudo().browse(payload["user_id"])
        if not user.exists() or not user.active:
            return request.make_json_response(
                {"status": "error", "message": "User not found or inactive"},
                status=401
            )

        request.jwt_user_id = payload["user_id"]
        return func(*args, **kwargs)
    return wrapper


# ================= CONTROLLER =================
class EmployeeAPIController(http.Controller):

    # ---------- LOGIN (GET JWT) ----------
    @http.route('/api/login', type="http", auth="public", methods=['POST'], csrf=False, cors='*')
    def api_login(self, **kwargs):
        try:
            body = request.httprequest.data
            if not body:
                return request.make_json_response({"status": "error", "message": "No data provided"}, status=400)

            payload = json.loads(body.decode('utf-8'))
            login = payload.get("login")
            password = payload.get("password")

            if not login or not password:
                return request.make_json_response({"status": "error", "message": "Login and password are required"}, status=400)

            # FIX: correct authenticate call
            uid = request.session.authenticate(request.session.db, login, password)
            if not uid:
                return request.make_json_response({"status": "error", "message": "Invalid credentials"}, status=401)

            token = generate_token(uid)
            user = request.env['res.users'].sudo().browse(uid)

            return request.make_json_response({
                "status": "success",
                "token": token,
                "user": {"id": user.id, "name": user.name, "login": user.login}
            }, status=200)

        except json.JSONDecodeError:
            return request.make_json_response({"status": "error", "message": "Invalid JSON payload"}, status=400)
        except Exception as e:
            return request.make_json_response({"status": "error", "message": str(e)}, status=500)


    # ---------- GET ALL EMPLOYEES ----------
    @http.route('/api/employees', type="http", auth="public", methods=['GET'], csrf=False, cors='*')
    @jwt_required
    def get_employees(self, **kwargs):
        try:
            limit = min(int(kwargs.get('limit', 100)), 1000)  # max 1000
            offset = int(kwargs.get('offset', 0))
            search = kwargs.get('search', '')

            domain = []
            if search:
                domain = ['|', ('name', 'ilike', search), ('work_email', 'ilike', search)]

            Employee = request.env['hr.employee'].with_user(request.jwt_user_id)
            total_count = Employee.search_count(domain)
            employees = Employee.search(domain, limit=limit, offset=offset, order='name')

            data = []
            for emp in employees:
                data.append({
                    "id": emp.id,
                    "name": emp.name,
                    "work_email": emp.work_email,
                    "job_title": emp.job_title,
                    "department": {"id": emp.department_id.id, "name": emp.department_id.name} if emp.department_id else None
                })

            return request.make_json_response({
                "status": "success",
                "data": data,
                "total": total_count,
                "limit": limit,
                "offset": offset
            }, status=200)

        except ValueError:
            return request.make_json_response({"status": "error", "message": "Invalid pagination parameters"}, status=400)
        except Exception as e:
            return request.make_json_response({"status": "error", "message": str(e)}, status=500)


    # ---------- GET SINGLE EMPLOYEE ----------
    @http.route('/api/employees/<int:emp_id>', type="http", auth="public", methods=['GET'], csrf=False, cors='*')
    @jwt_required
    def get_single_employee(self, emp_id, **kwargs):
        try:
            Employee = request.env['hr.employee'].with_user(request.jwt_user_id)
            emp = Employee.browse(emp_id)

            if not emp.exists():
                return request.make_json_response({"status": "error", "message": "Employee not found"}, status=404)

            data = {
                "id": emp.id,
                "name": emp.name,
                "work_email": emp.work_email,
                "work_phone": emp.work_phone,
                "job_title": emp.job_title,
                "department": {"id": emp.department_id.id, "name": emp.department_id.name} if emp.department_id else None,
                "parent": {"id": emp.parent_id.id, "name": emp.parent_id.name} if emp.parent_id else None,
                "work_location": {"id": emp.work_location_id.id, "name": emp.work_location_id.name} if emp.work_location_id else None,
                "company": {"id": emp.company_id.id, "name": emp.company_id.name} if emp.company_id else None
            }

            return request.make_json_response({"status": "success", "data": data}, status=200)

        except Exception as e:
            return request.make_json_response({"status": "error", "message": str(e)}, status=500)


    # ---------- CREATE EMPLOYEE ----------
    @http.route('/api/employees', type="http", auth="public", methods=['POST'], csrf=False, cors='*')
    @jwt_required
    def create_employee(self, **kwargs):
        try:
            body = request.httprequest.data
            if not body:
                return request.make_json_response({"status": "error", "message": "No data provided"}, status=400)

            payload = json.loads(body.decode('utf-8'))
            name = payload.get("name")
            if not name:
                return request.make_json_response({"status": "error", "message": "Employee name is required"}, status=400)

            vals = {
                "name": name,
                "work_email": payload.get("work_email"),
                "work_phone": payload.get("work_phone"),
                "job_title": payload.get("job_title"),
                "department_id": payload.get("department_id"),
                "parent_id": payload.get("parent_id"),
                "work_location_id": payload.get("work_location_id")
            }

            # Remove None values
            vals = {k: v for k, v in vals.items() if v is not None}

            Employee = request.env['hr.employee'].with_user(request.jwt_user_id)
            emp = Employee.create(vals)

            data = {
                "id": emp.id,
                "name": emp.name,
                "work_email": emp.work_email,
                "job_title": emp.job_title
            }

            return request.make_json_response({"status": "success", "message": "Employee created successfully", "data": data}, status=201)

        except json.JSONDecodeError:
            return request.make_json_response({"status": "error", "message": "Invalid JSON payload"}, status=400)
        except Exception as e:
            return request.make_json_response({"status": "error", "message": str(e)}, status=500)


    # ---------- UPDATE EMPLOYEE ----------
    @http.route('/api/employees/<int:emp_id>', type="http", auth="public", methods=['PUT'], csrf=False, cors='*')
    @jwt_required
    def update_employee(self, emp_id, **kwargs):
        try:
            body = request.httprequest.data
            if not body:
                return request.make_json_response({"status": "error", "message": "No data provided"}, status=400)

            payload = json.loads(body.decode('utf-8'))

            Employee = request.env['hr.employee'].with_user(request.jwt_user_id)
            emp = Employee.browse(emp_id)

            if not emp.exists():
                return request.make_json_response({"status": "error", "message": "Employee not found"}, status=404)

            allowed_fields = ['name', 'work_email', 'work_phone', 'job_title', 'department_id', 'parent_id', 'work_location_id']
            vals = {k: payload[k] for k in allowed_fields if k in payload}

            if not vals:
                return request.make_json_response({"status": "error", "message": "No valid fields provided to update"}, status=400)

            emp.write(vals)
            data = {
                "id": emp.id,
                "name": emp.name,
                "work_email": emp.work_email,
                "job_title": emp.job_title
            }

            return request.make_json_response({"status": "success", "message": "Employee updated successfully", "data": data}, status=200)

        except json.JSONDecodeError:
            return request.make_json_response({"status": "error", "message": "Invalid JSON payload"}, status=400)
        except Exception as e:
            return request.make_json_response({"status": "error", "message": str(e)}, status=500)


    # ---------- DELETE EMPLOYEE ----------
    @http.route('/api/employees/<int:emp_id>', type="http", auth="public", methods=['DELETE'], csrf=False, cors='*')
    @jwt_required
    def delete_employee(self, emp_id, **kwargs):
        try:
            Employee = request.env['hr.employee'].with_user(request.jwt_user_id)
            emp = Employee.browse(emp_id)

            if not emp.exists():
                return request.make_json_response({"status": "error", "message": "Employee not found"}, status=404)

            name = emp.name
            emp.unlink()

            return request.make_json_response({"status": "success", "message": f"Employee '{name}' (ID: {emp_id}) deleted successfully"}, status=200)

        except Exception as e:
            return request.make_json_response({"status": "error", "message": str(e)}, status=500)
